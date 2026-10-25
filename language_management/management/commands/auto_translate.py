import os
import re
import time
import urllib.parse
import urllib.request
import json
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
import polib


class Command(BaseCommand):
    help = "Automatically translates untranslated gettext catalog (.po) strings to provide a starting baseline for Rosetta review."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lang",
            "-l",
            type=str,
            help="Specific language code to translate (e.g. es, pt, fr, it, ja). Defaults to all target languages.",
        )
        parser.add_argument(
            "--backend",
            "-b",
            type=str,
            default="mymemory",
            choices=["mymemory", "deepl", "openai"],
            help="Translation backend to use. Defaults to 'mymemory' (free tier, no API key required).",
        )
        parser.add_argument(
            "--mark-fuzzy",
            action="store_true",
            default=False,
            help="Mark auto-translated entries as fuzzy for manual Rosetta review (disabled by default so translations compile cleanly into .mo).",
        )
        parser.add_argument(
            "--no-fuzzy",
            action="store_true",
            help="Ensure auto-translated entries are not marked fuzzy (default).",
        )
        parser.add_argument(
            "--unfuzzy-all",
            action="store_true",
            help="Strip the fuzzy flag from all non-empty translated entries across catalogs and recompile .mo.",
        )
        parser.add_argument(
            "--include-fuzzy",
            action="store_true",
            default=True,
            help="Include existing fuzzy entries when translating so they do not get trapped in uncompiled limbo (default: True).",
        )
        parser.add_argument(
            "--skip-mismatched-fuzzy",
            action="store_true",
            help="Skip re-translating entries that gettext marked fuzzy with previous mismatched msgids.",
        )
        parser.add_argument(
            "--no-compile",
            action="store_true",
            help="Skip compiling .mo files after translation.",
        )
        parser.add_argument(
            "--max",
            type=int,
            default=None,
            help="Maximum number of strings to translate per language (useful for testing or avoiding rate limits).",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.15,
            help="Delay in seconds between translation requests (default: 0.15s).",
        )

    def handle(self, *args, **options):
        target_lang = options.get("lang")
        backend = options.get("backend")
        mark_fuzzy = options.get("mark_fuzzy", False)
        if options.get("no_fuzzy"):
            mark_fuzzy = False
        unfuzzy_all = options.get("unfuzzy_all", False)
        include_fuzzy = options.get("include_fuzzy", True)
        skip_mismatched = options.get("skip_mismatched_fuzzy")
        auto_compile = not options.get("no_compile")
        max_entries = options.get("max")
        delay = options.get("delay")

        locale_dir = Path(settings.BASE_DIR) / "locale"
        if not locale_dir.exists():
            self.stderr.write(self.style.ERROR(f"Locale directory not found at: {locale_dir}"))
            return

        available_languages = [
            code for code, name in settings.LANGUAGES if code != "en"
        ]

        if target_lang:
            if target_lang not in available_languages:
                self.stderr.write(
                    self.style.ERROR(
                        f"Target language '{target_lang}' is not in settings.LANGUAGES: {available_languages}"
                    )
                )
                return
            languages_to_process = [target_lang]
        else:
            languages_to_process = available_languages

        if unfuzzy_all:
            self.stdout.write(self.style.MIGRATE_HEADING("Stripping fuzzy flags from non-empty translated entries..."))
            total_unfuzzied = 0
            for lang_code in languages_to_process:
                po_file = locale_dir / lang_code / "LC_MESSAGES" / "django.po"
                if not po_file.exists():
                    continue
                po = polib.pofile(str(po_file))
                unfuzzied = 0
                for entry in po:
                    if "fuzzy" in entry.flags and entry.msgstr.strip():
                        entry.flags.remove("fuzzy")
                        if getattr(entry, "previous_msgid", None):
                            entry.previous_msgid = None
                        unfuzzied += 1
                if unfuzzied > 0:
                    po.save(str(po_file))
                self.stdout.write(self.style.SUCCESS(f"Unfuzzied {unfuzzied} entries in [{lang_code}]."))
                total_unfuzzied += unfuzzied
            if auto_compile:
                self.stdout.write(self.style.MIGRATE_HEADING("\nCompiling message catalogs (.mo)..."))
                call_command("compilemessages", ignore=[".venv"])
                self.stdout.write(self.style.SUCCESS(f"All message catalogs compiled successfully ({total_unfuzzied} entries unfuzzied)."))
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Starting Auto-Translation Baseline Engine [Backend: {backend}]"
            )
        )
        self.stdout.write(f"Target languages: {', '.join(languages_to_process)}")
        self.stdout.write(f"Mark as fuzzy for Rosetta review: {mark_fuzzy}")

        for lang_code in languages_to_process:
            po_file = locale_dir / lang_code / "LC_MESSAGES" / "django.po"
            if not po_file.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"PO catalog does not exist for '{lang_code}' at {po_file}. Skipping."
                    )
                )
                continue

            po = polib.pofile(str(po_file))
            
            # Find untranslated entries, existing fuzzy entries, and mismatched previous_msgid
            entries_to_translate = []
            for entry in po:
                if entry.obsolete:
                    continue
                if not entry.msgstr:
                    entries_to_translate.append(entry)
                elif not skip_mismatched and getattr(entry, "previous_msgid", None):
                    entries_to_translate.append(entry)
                elif include_fuzzy and "fuzzy" in entry.flags:
                    entries_to_translate.append(entry)

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n--- Processing [{lang_code}] ({len(entries_to_translate)} pending entries) ---"
                )
            )

            if not entries_to_translate:
                self.stdout.write(f"No entries needing translation for {lang_code}.")
                continue

            count = 0
            success_count = 0

            for entry in entries_to_translate:
                if max_entries and count >= max_entries:
                    self.stdout.write(f"Reached max limit of {max_entries} entries.")
                    break

                text_to_translate = entry.msgid.strip()
                if not text_to_translate:
                    continue

                translated_text = self._translate_string(
                    text_to_translate, target_lang=lang_code, backend=backend
                )

                if translated_text:
                    entry.msgstr = translated_text
                    if getattr(entry, "previous_msgid", None):
                        entry.previous_msgid = None
                    if mark_fuzzy and "fuzzy" not in entry.flags:
                        entry.flags.append("fuzzy")
                    elif not mark_fuzzy and "fuzzy" in entry.flags:
                        entry.flags.remove("fuzzy")
                    success_count += 1

                # If plural entry exists, translate plural form as well
                if entry.msgid_plural:
                    translated_plural = self._translate_string(
                        entry.msgid_plural.strip(), target_lang=lang_code, backend=backend
                    )
                    if translated_plural:
                        entry.msgstr_plural[0] = entry.msgstr or translated_text
                        entry.msgstr_plural[1] = translated_plural

                count += 1
                if count % 15 == 0 or count == len(entries_to_translate):
                    self.stdout.write(f"  Translated {count}/{len(entries_to_translate)} strings...")

                if delay > 0:
                    time.sleep(delay)

            po.save(str(po_file))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Saved {success_count} translated strings to {po_file}."
                )
            )

        if auto_compile:
            self.stdout.write(self.style.MIGRATE_HEADING("\nCompiling message catalogs (.mo)..."))
            try:
                compile_kwargs = {"ignore": [".venv"]}
                if mark_fuzzy:
                    compile_kwargs["fuzzy"] = True
                call_command("compilemessages", **compile_kwargs)
                self.stdout.write(self.style.SUCCESS("All message catalogs compiled successfully."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error compiling messages: {e}"))

    def _protect_placeholders(self, text):
        """Replaces format placeholders (e.g. %(var)s, {var}, {{ var }}, %s) with safe tokens."""
        placeholders = []

        def repl(match):
            placeholders.append(match.group(0))
            return f"[[PH{len(placeholders) - 1}]]"

        # Match Python %(name)s, %s, %d, Django {{ var }}, {% tag %}
        pattern = re.compile(
            r"(%\([a-zA-Z0-9_]+\)[sfd]|%[sfd]|{{[^}]+}}|{%[^%]+%}|%[0-9]*\.[0-9]*[f]|%[0-9]+[sfd])"
        )
        safe_text = pattern.sub(repl, text)
        return safe_text, placeholders

    def _restore_placeholders(self, text, placeholders):
        """Restores protected placeholders from safe tokens."""
        result = text
        for i, ph in enumerate(placeholders):
            token_pattern = re.compile(rf"\[\[\s*PH{i}\s*\]\]", re.IGNORECASE)
            result = token_pattern.sub(ph, result)
        return result

    def _translate_string(self, text, target_lang, backend):
        """Translates a single string using the selected backend with placeholder preservation."""
        safe_text, placeholders = self._protect_placeholders(text)

        translated = None
        if backend == "mymemory":
            translated = self._translate_mymemory(safe_text, target_lang)
        elif backend == "deepl":
            translated = self._translate_deepl(safe_text, target_lang)
        elif backend == "openai":
            translated = self._translate_openai(safe_text, target_lang)

        if not translated:
            return None

        final_text = self._restore_placeholders(translated, placeholders)
        return final_text

    def _translate_mymemory(self, text, target_lang):
        """Free MyMemory API translation."""
        try:
            encoded_query = urllib.parse.quote(text)
            url = f"https://api.mymemory.translated.net/get?q={encoded_query}&langpair=en|{target_lang}"
            
            # If developer set an email in env/settings, MyMemory increases free daily quota to 10k words
            email = getattr(settings, "MYMEMORY_EMAIL", os.environ.get("MYMEMORY_EMAIL", ""))
            if email:
                url += f"&de={urllib.parse.quote(email)}"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EnterpriseWebsite/1.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                res_data = payload.get("responseData")
                if res_data and "translatedText" in res_data:
                    return res_data["translatedText"]
        except Exception:
            return None
        return None

    def _translate_deepl(self, text, target_lang):
        """DeepL API translation using DEEPL_AUTH_KEY."""
        api_key = getattr(settings, "DEEPL_AUTH_KEY", os.environ.get("DEEPL_AUTH_KEY", ""))
        if not api_key:
            return None
        try:
            import requests
            endpoint = (
                "https://api-free.deepl.com/v2/translate"
                if ":fx" in api_key
                else "https://api.deepl.com/v2/translate"
            )
            # DeepL uses 'PT-PT' or 'PT-BR' instead of generic 'pt'
            dl_lang = target_lang.upper()
            if dl_lang == "PT":
                dl_lang = "PT-PT"

            resp = requests.post(
                endpoint,
                headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                data={"text": text, "target_lang": dl_lang, "source_lang": "EN"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                translations = data.get("translations", [])
                if translations:
                    return translations[0].get("text")
        except Exception:
            return None
        return None

    def _translate_openai(self, text, target_lang):
        """OpenAI API translation using OPENAI_API_KEY."""
        api_key = getattr(settings, "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        if not api_key:
            return None
        try:
            import requests
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are a professional software localization translator. Translate from English into language code '{target_lang}'. Return ONLY the translation, preserving exact casing and tokens like [[PH0]].",
                        },
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.2,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None
        return None
