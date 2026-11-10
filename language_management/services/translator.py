import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Base error for translation operations."""
    pass


class RateLimitExceededError(TranslationError):
    """Raised when an external translation backend exceeds rate limits (e.g. HTTP 429)."""
    pass


class PlaceholderManager:
    """Safely extracts and restores code and template placeholders during translation."""

    PLACEHOLDER_REGEX = re.compile(
        r"(%\([a-zA-Z0-9_]+\)[sfd]|%[sfd]|{{[^}]+}}|{%[^%]+%}|%[0-9]*\.[0-9]*[f]|%[0-9]+[sfd])"
    )
    FORMAT_SPEC_REGEX = re.compile(
        r"(%\([a-zA-Z0-9_]+\)[sfd]|%[sfd]|%[0-9]*\.[0-9]*[f]|%[0-9]+[sfd])"
    )

    @classmethod
    def protect(cls, text: str) -> Tuple[str, List[str]]:
        placeholders: List[str] = []

        def repl(match):
            placeholders.append(match.group(0))
            return f"__PH_{len(placeholders) - 1}__"

        safe_text = cls.PLACEHOLDER_REGEX.sub(repl, text)
        return safe_text, placeholders

    @classmethod
    def restore(cls, text: str, placeholders: List[str]) -> str:
        result = text
        for i, ph in enumerate(placeholders):
            token_pattern = re.compile(
                rf"(?:__|\[\[?)\s*PH_?\s*{i}\s*(?:__|\]\]?)", re.IGNORECASE
            )
            result = token_pattern.sub(ph, result)
        return result

    @classmethod
    def extract_format_specs(cls, text: str) -> List[str]:
        return cls.FORMAT_SPEC_REGEX.findall(text)

    @classmethod
    def validate_format_specs(
        cls, msgid: str, msgstr: str, is_python_format: bool = False
    ) -> bool:
        if not msgstr:
            return True

        if is_python_format or "%" in msgid:
            expected = sorted(cls.extract_format_specs(msgid))
            actual = sorted(cls.extract_format_specs(msgstr))
            if expected != actual:
                return False

        if msgid.startswith("\n") and not msgstr.startswith("\n"):
            return False
        if msgid.endswith("\n") and not msgstr.endswith("\n"):
            return False

        return True

    @classmethod
    def preserve_boundary_whitespace(cls, original: str, translated: str) -> str:
        if not translated:
            return translated

        leading_ws = ""
        for char in original:
            if char in " \t\r\n":
                leading_ws += char
            else:
                break

        trailing_ws = ""
        for char in reversed(original):
            if char in " \t\r\n":
                trailing_ws = char + trailing_ws
            else:
                break

        return f"{leading_ws}{translated.strip()}{trailing_ws}"


class BaseTranslationBackend:
    """Abstract base for translation backends."""

    def translate(self, text: str, target_lang: str) -> Optional[str]:
        raise NotImplementedError

    def translate_batch(
        self, texts: List[str], target_lang: str
    ) -> List[Optional[str]]:
        return [self.translate(t, target_lang) for t in texts]


class GoogleWebBackend(BaseTranslationBackend):
    """Zero-dependency, reliable Google Translate web endpoint with smart batching and retry."""

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EnterpriseWebsite/1.0"
    BATCH_DELIM = "\n__DELIM__\n"

    def translate(self, text: str, target_lang: str) -> Optional[str]:
        res = self.translate_batch([text], target_lang)
        return res[0] if res else None

    def translate_batch(
        self, texts: List[str], target_lang: str
    ) -> List[Optional[str]]:
        if not texts:
            return []

        lang = target_lang.lower()
        if lang == "zh-hans":
            lang = "zh-CN"
        elif lang == "zh-hant":
            lang = "zh-TW"

        if len(texts) == 1:
            return [self._translate_single(texts[0], lang)]

        # Attempt delimited batch request
        joined = self.BATCH_DELIM.join([t.replace("\r", "") for t in texts])
        try:
            encoded_query = urllib.parse.quote(joined)
            url = (
                f"https://translate.googleapis.com/translate_a/single"
                f"?client=gtx&sl=en&tl={lang}&dt=t&q={encoded_query}"
            )
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data and isinstance(data, list) and data[0]:
                    full_translated = "".join(
                        seg[0] for seg in data[0] if seg and isinstance(seg, list) and seg[0]
                    )
                    parts = re.split(r"\s*__DELIM__\s*", full_translated)
                    if len(parts) == len(texts):
                        return [p.strip() for p in parts]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimitExceededError("Google Translate web endpoint rate limit encountered (HTTP 429).")
            logger.warning("Google Translate batch error HTTP %s: %s", e.code, e)
        except Exception as exc:
            logger.warning("Google Translate batch error: %s; falling back to single items", exc)

        # Fallback to single item translation if batch delimiter parsing failed
        return [self._translate_single(t, lang) for t in texts]

    def _translate_single(self, text: str, lang: str) -> Optional[str]:
        if not text.strip():
            return text

        encoded_query = urllib.parse.quote(text)
        url = (
            f"https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=en&tl={lang}&dt=t&q={encoded_query}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data and isinstance(data, list) and data[0]:
                    parts = [
                        seg[0] for seg in data[0] if seg and isinstance(seg, list) and seg[0]
                    ]
                    return "".join(parts)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimitExceededError("Google Translate web endpoint rate limit encountered (HTTP 429).")
            return None
        except Exception:
            return None
        return None


class GeminiBackend(BaseTranslationBackend):
    """Google Gemini API backend supporting structured batch translations."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or getattr(settings, "GEMINI_API_KEY", "")
            or getattr(settings, "GOOGLE_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
            or os.environ.get("GOOGLE_API_KEY", "")
        )

    def translate(self, text: str, target_lang: str) -> Optional[str]:
        batch_res = self.translate_batch([text], target_lang)
        return batch_res[0] if batch_res else None

    def translate_batch(
        self, texts: List[str], target_lang: str
    ) -> List[Optional[str]]:
        if not self.api_key:
            logger.warning("GeminiBackend called without GEMINI_API_KEY or GOOGLE_API_KEY.")
            return [None] * len(texts)

        if not texts:
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        payload_items = [{"id": i, "text": t} for i, t in enumerate(texts)]
        prompt = (
            f"You are a professional software localization system. Translate the following array of English strings "
            f"into target language '{target_lang}'.\n"
            f"Preserve all tokens like __PH_0__, __PH_1__, formatting, and exact linebreaks.\n"
            f"Return ONLY a valid JSON array of objects with keys 'id' (int) and 'translation' (string).\n\n"
            f"{json.dumps(payload_items, ensure_ascii=False)}"
        )

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                raw_text = (
                    res_json.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                items = json.loads(raw_text)
                mapping = {item["id"]: item["translation"] for item in items if "id" in item and "translation" in item}
                return [mapping.get(i) for i in range(len(texts))]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimitExceededError("Gemini API rate limit exceeded (HTTP 429).")
            logger.warning("Gemini API HTTP error %s", e.code)
            return [None] * len(texts)
        except Exception as exc:
            logger.warning("Gemini API request error: %s", exc)
            return [None] * len(texts)


class DeepLBackend(BaseTranslationBackend):
    """DeepL API translation backend."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or getattr(settings, "DEEPL_AUTH_KEY", "")
            or os.environ.get("DEEPL_AUTH_KEY", "")
        )

    def translate(self, text: str, target_lang: str) -> Optional[str]:
        if not self.api_key:
            return None

        try:
            import requests

            endpoint = (
                "https://api-free.deepl.com/v2/translate"
                if ":fx" in self.api_key
                else "https://api.deepl.com/v2/translate"
            )
            dl_lang = target_lang.upper()
            if dl_lang == "PT":
                dl_lang = "PT-PT"

            resp = requests.post(
                endpoint,
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data={"text": text, "target_lang": dl_lang, "source_lang": "EN"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                translations = data.get("translations", [])
                if translations:
                    return translations[0].get("text")
            elif resp.status_code == 429:
                raise RateLimitExceededError("DeepL rate limit encountered.")
        except RateLimitExceededError:
            raise
        except Exception as exc:
            logger.warning("DeepL error: %s", exc)
            return None
        return None


class OpenAIBackend(BaseTranslationBackend):
    """OpenAI API translation backend."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or getattr(settings, "OPENAI_API_KEY", "")
            or os.environ.get("OPENAI_API_KEY", "")
        )

    def translate(self, text: str, target_lang: str) -> Optional[str]:
        if not self.api_key:
            return None

        try:
            import requests

            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"You are a professional software localization translator. "
                                f"Translate from English into language code '{target_lang}'. "
                                f"Return ONLY the translation, preserving exact casing and tokens like [[PH0]]."
                            ),
                        },
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.2,
                },
                timeout=12,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            elif resp.status_code == 429:
                raise RateLimitExceededError("OpenAI rate limit encountered.")
        except RateLimitExceededError:
            raise
        except Exception as exc:
            logger.warning("OpenAI translation error: %s", exc)
            return None
        return None


class MyMemoryBackend(BaseTranslationBackend):
    """MyMemory API translation backend with explicit 429 / quota error detection."""

    def translate(self, text: str, target_lang: str) -> Optional[str]:
        try:
            encoded_query = urllib.parse.quote(text)
            url = f"https://api.mymemory.translated.net/get?q={encoded_query}&langpair=en|{target_lang}"
            email = getattr(settings, "MYMEMORY_EMAIL", os.environ.get("MYMEMORY_EMAIL", ""))
            if email:
                url += f"&de={urllib.parse.quote(email)}"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EnterpriseWebsite/1.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                status = payload.get("responseStatus")
                if status in (403, 429):
                    raise RateLimitExceededError(
                        f"MyMemory daily quota exceeded (Status: {status}). Switch to --backend google or add API key."
                    )
                res_data = payload.get("responseData")
                if res_data and "translatedText" in res_data:
                    res_text = res_data["translatedText"]
                    if "MYMEMORY WARNING" in res_text.upper():
                        raise RateLimitExceededError(
                            "MyMemory returned quota warning: Daily quota exhausted."
                        )
                    return res_text
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise RateLimitExceededError(
                    f"MyMemory HTTP {e.code} error: Daily rate limit or quota exceeded."
                )
            return None
        except RateLimitExceededError:
            raise
        except Exception:
            return None
        return None


def get_translation_backend(name: str) -> BaseTranslationBackend:
    """Factory to return initialized translation backend."""
    name = (name or "google").lower()
    if name in ("google", "google_web", "deep_translator"):
        return GoogleWebBackend()
    elif name == "gemini":
        return GeminiBackend()
    elif name == "deepl":
        return DeepLBackend()
    elif name == "openai":
        return OpenAIBackend()
    elif name == "mymemory":
        return MyMemoryBackend()
    raise ValueError(f"Unknown translation backend: '{name}'")
