"""Optional AI project blueprint advisor for `manage.py create_site --ai`."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

from .manifest import (
    OPTIONAL_PLUGIN_APPS,
    SUPPORTED_DATABASES,
    SUPPORTED_LANGUAGES,
    SUPPORTED_THEMES,
    SiteManifest,
)

logger = logging.getLogger(__name__)

DEFAULT_ADVISOR_MODEL = "gemini-2.5-flash"

_PLUGIN_KEYWORD_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("crm", ("crm", "sales", "lead", "leads", "contact", "contacts", "customer", "pipeline", "funnel")),
    ("erp", ("erp", "inventory", "invoice", "invoices", "catalog", "product", "products", "ecommerce", "warehouse", "stock")),
    ("intelligent_tracker_hub", ("security", "camera", "cameras", "vision", "tracker", "surveillance", "anpr", "soc", "intrusion")),
    ("video_gallery", ("video", "videos", "media", "gallery", "stream", "youtube", "vimeo")),
    ("todo", ("todo", "task", "tasks", "checklist", "action item")),
    ("polls", ("poll", "polls", "survey", "surveys", "vote", "voting")),
    ("task_runner", ("celery", "async", "worker", "workers", "background", "queue")),
    ("rest_api", ("api", "rest", "openapi", "swagger", "endpoint", "endpoints")),
    ("webprogram", ("brython", "labs", "python browser", "webprogram", "sandbox")),
)

_LANGUAGE_KEYWORD_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("es", ("spanish", "espanol", "bilingual", "latam")),
    ("pt", ("portuguese", "portugues", "brazil")),
    ("fr", ("french", "francais")),
    ("it", ("italian", "italiano")),
    ("ja", ("japanese", "japan")),
)


def _match_keywords(text: str, keywords: Tuple[str, ...]) -> bool:
    """Return True if any keyword matches as a whole word/phrase in lowercased text."""
    return any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords)


def _extract_json_payload(raw_text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from model text, stripping optional Markdown code fences."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_advisor_endpoint() -> str:
    """Resolve advisor HTTPS endpoint from environment without hardcoded non-TLS hosts."""
    custom_endpoint = os.getenv("GEMINI_API_ENDPOINT", "").strip()
    if custom_endpoint:
        parsed = urllib.parse.urlparse(custom_endpoint)
        if parsed.scheme != "https":
            raise ValueError("GEMINI_API_ENDPOINT must use the https:// scheme.")
        return custom_endpoint
    model_name = os.getenv("GEMINI_ADVISOR_MODEL", DEFAULT_ADVISOR_MODEL).strip() or DEFAULT_ADVISOR_MODEL
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"


def _call_gemini_advisor(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Query the Gemini API for structured site blueprint JSON; return None on failure."""
    instruction = (
        "Return ONLY valid JSON with keys: plugins (subset of "
        f"{list(OPTIONAL_PLUGIN_APPS)}), theme (one of {list(SUPPORTED_THEMES)}), "
        f"languages (subset of {list(SUPPORTED_LANGUAGES)}), database (one of {list(SUPPORTED_DATABASES)}), "
        "homepage_headline (<= 80 chars), homepage_subheadline (<= 160 chars). "
        f"Project brief: {prompt}"
    )
    body = json.dumps({"contents": [{"parts": [{"text": instruction}]}]}).encode("utf-8")
    try:
        endpoint = _build_advisor_endpoint()
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return _extract_json_payload(text)
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("AI blueprint advisor request failed; falling back to heuristic advisor: %s", exc)
        return None


def _heuristic_blueprint_from_prompt(prompt: str, manifest: SiteManifest) -> SiteManifest:
    """Deterministically infer plugins, theme, database, languages, and copy from prompt text."""
    lower = (prompt or "").strip().lower()
    plugins: List[str] = [
        slug for slug, keywords in _PLUGIN_KEYWORD_RULES if _match_keywords(lower, keywords)
    ]
    theme = "bootstrap5"
    if _match_keywords(lower, ("tailwind",)):
        theme = "tailwind"
    elif _match_keywords(lower, ("minimal", "minimalist")):
        theme = "minimal"

    database = "sqlite"
    if _match_keywords(lower, ("postgres", "postgresql")):
        database = "postgres"
    elif _match_keywords(lower, ("mysql", "mariadb")):
        database = "mysql"

    languages = ["en"] + [
        code for code, keywords in _LANGUAGE_KEYWORD_RULES if _match_keywords(lower, keywords)
    ]
    clean_prompt = " ".join((prompt or "").split())
    headline = manifest.display_name or manifest.project_name.replace("_", " ").title()
    if clean_prompt:
        headline = clean_prompt[:77].rstrip("., ") + ("..." if len(clean_prompt) > 77 else "")
    subheadline = (
        clean_prompt[:157].rstrip("., ") + ("..." if len(clean_prompt) > 157 else "")
        if clean_prompt
        else "Composable enterprise web platform powered by Django and Wagtail."
    )

    manifest.plugins = plugins
    manifest.theme = theme
    manifest.database = database
    manifest.languages = languages
    manifest.homepage_headline = headline
    manifest.homepage_subheadline = subheadline
    manifest.validate()
    return manifest


def _apply_ai_suggestion(suggestion: Dict[str, Any], manifest: SiteManifest) -> SiteManifest:
    """Apply validated AI response fields onto a SiteManifest copy."""
    raw_plugins = suggestion.get("plugins")
    if isinstance(raw_plugins, list):
        manifest.plugins = [str(p) for p in raw_plugins if str(p).strip().lower() in OPTIONAL_PLUGIN_APPS]
    raw_theme = str(suggestion.get("theme", "")).strip().lower()
    if raw_theme in SUPPORTED_THEMES:
        manifest.theme = raw_theme
    raw_db = str(suggestion.get("database", "")).strip().lower()
    if raw_db in SUPPORTED_DATABASES:
        manifest.database = raw_db
    raw_langs = suggestion.get("languages")
    if isinstance(raw_langs, list):
        valid_langs = [str(code).strip().lower() for code in raw_langs if str(code).strip().lower() in SUPPORTED_LANGUAGES]
        if valid_langs:
            manifest.languages = valid_langs
    if isinstance(suggestion.get("homepage_headline"), str) and suggestion["homepage_headline"].strip():
        manifest.homepage_headline = suggestion["homepage_headline"].strip()[:120]
    if isinstance(suggestion.get("homepage_subheadline"), str) and suggestion["homepage_subheadline"].strip():
        manifest.homepage_subheadline = suggestion["homepage_subheadline"].strip()[:240]
    manifest.validate()
    return manifest


def suggest_manifest_from_prompt(
    prompt: str,
    base_manifest: Optional[SiteManifest] = None,
) -> SiteManifest:
    """Suggest a validated SiteManifest from a natural-language project brief."""
    manifest = (
        SiteManifest.from_dict(base_manifest.to_dict())
        if base_manifest is not None
        else SiteManifest(project_name="enterprise_site", description=prompt or "Enterprise Django site.")
    )
    if prompt and not manifest.description:
        manifest.description = prompt.strip()

    api_key = (os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")).strip()
    if api_key and (prompt or "").strip():
        suggestion = _call_gemini_advisor(prompt.strip(), api_key)
        if suggestion is not None:
            return _apply_ai_suggestion(suggestion, manifest)

    return _heuristic_blueprint_from_prompt(prompt, manifest)
