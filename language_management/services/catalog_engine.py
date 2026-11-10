import logging
import time
from pathlib import Path
from typing import Callable, List, Optional

import polib

from .translator import (
    BaseTranslationBackend,
    PlaceholderManager,
    RateLimitExceededError,
    get_translation_backend,
)

logger = logging.getLogger(__name__)


class CatalogTranslationStats:
    def __init__(self, total_pending: int):
        self.total_pending = total_pending
        self.processed = 0
        self.succeeded = 0
        self.failed = 0
        self.rate_limited = False


class CatalogTranslationEngine:
    """Manages reading, translating, validating, checkpointing, and saving gettext catalogs."""

    def __init__(
        self,
        backend_name: str = "google",
        mark_fuzzy: bool = False,
        include_fuzzy: bool = True,
        skip_mismatched: bool = False,
        delay: float = 0.05,
        checkpoint_interval: int = 50,
        batch_size: int = 20,
        stdout_write: Optional[Callable[[str], None]] = None,
        style=None,
    ):
        self.backend_name = backend_name
        self.backend: BaseTranslationBackend = get_translation_backend(backend_name)
        self.mark_fuzzy = mark_fuzzy
        self.include_fuzzy = include_fuzzy
        self.skip_mismatched = skip_mismatched
        self.delay = delay
        self.checkpoint_interval = checkpoint_interval
        self.batch_size = batch_size
        self.write = stdout_write or (lambda msg: None)
        self.style = style

    def get_pending_entries(self, po: polib.POFile) -> List[polib.POEntry]:
        """Filters catalog for entries that require translation."""
        entries: List[polib.POEntry] = []
        for entry in po:
            if entry.obsolete:
                continue
            if not entry.msgstr:
                entries.append(entry)
            elif not self.skip_mismatched and getattr(entry, "previous_msgid", None):
                entries.append(entry)
            elif self.include_fuzzy and "fuzzy" in entry.flags:
                entries.append(entry)
        return entries

    def process_catalog(
        self,
        po_path: Path,
        target_lang: str,
        max_entries: Optional[int] = None,
    ) -> CatalogTranslationStats:
        """Processes a single PO catalog file with batched translations and honest progress reporting."""
        po = polib.pofile(str(po_path))
        pending = self.get_pending_entries(po)
        stats = CatalogTranslationStats(len(pending))

        if not pending:
            return stats

        entries_to_process = pending[:max_entries] if max_entries else pending
        total_to_process = len(entries_to_process)

        # Process in batches
        chunk_size = max(1, self.batch_size)
        for i in range(0, total_to_process, chunk_size):
            chunk = entries_to_process[i : i + chunk_size]
            prepared = []
            for entry in chunk:
                raw_msgid = entry.msgid
                text_to_translate = raw_msgid.strip()
                if not text_to_translate:
                    prepared.append((entry, None, []))
                    continue
                safe_text, placeholders = PlaceholderManager.protect(text_to_translate)
                prepared.append((entry, safe_text, placeholders))

            texts_to_call = [p[1] for p in prepared if p[1] is not None]
            translated_results: List[Optional[str]] = []

            if texts_to_call:
                try:
                    translated_results = self.backend.translate_batch(
                        texts_to_call, target_lang=target_lang
                    )
                except RateLimitExceededError as e:
                    stats.rate_limited = True
                    msg = f"\n[Rate Limit Exceeded] Backend '{self.backend_name}' was throttled: {e}"
                    self.write(self.style.ERROR(msg) if self.style else msg)
                    break
                except Exception as exc:
                    logger.error("Batch translation call error: %s", exc)
                    translated_results = [None] * len(texts_to_call)

            res_iter = iter(translated_results)
            for entry, safe_text, placeholders in prepared:
                stats.processed += 1
                if safe_text is None:
                    stats.failed += 1
                    continue

                raw_translated = next(res_iter, None)
                if not raw_translated:
                    stats.failed += 1
                    continue

                final_text = PlaceholderManager.restore(raw_translated, placeholders)
                candidate_msgstr = PlaceholderManager.preserve_boundary_whitespace(
                    entry.msgid, final_text
                )

                is_python_format = "python-format" in entry.flags
                if not PlaceholderManager.validate_format_specs(
                    entry.msgid, candidate_msgstr, is_python_format=is_python_format
                ):
                    stats.failed += 1
                    continue

                entry.msgstr = candidate_msgstr
                if getattr(entry, "previous_msgid", None):
                    entry.previous_msgid = None

                if self.mark_fuzzy and "fuzzy" not in entry.flags:
                    entry.flags.append("fuzzy")
                elif not self.mark_fuzzy and "fuzzy" in entry.flags:
                    entry.flags.remove("fuzzy")

                # Handle plural entry if present
                if entry.msgid_plural:
                    p_safe, p_ph = PlaceholderManager.protect(entry.msgid_plural.strip())
                    p_trans = self.backend.translate(p_safe, target_lang=target_lang)
                    if p_trans:
                        p_final = PlaceholderManager.restore(p_trans, p_ph)
                        c_plural = PlaceholderManager.preserve_boundary_whitespace(
                            entry.msgid_plural, p_final
                        )
                        if PlaceholderManager.validate_format_specs(
                            entry.msgid_plural, c_plural, is_python_format=is_python_format
                        ):
                            entry.msgstr_plural[0] = entry.msgstr
                            entry.msgstr_plural[1] = c_plural

                stats.succeeded += 1

            # Progress notification
            progress_msg = (
                f"  Processed {stats.processed}/{total_to_process} entries | "
                f"Success: {stats.succeeded} | Failed: {stats.failed}"
            )
            self.write(self.style.SUCCESS(progress_msg) if self.style else progress_msg)

            # Atomic checkpoint save
            if stats.processed % self.checkpoint_interval < chunk_size or stats.processed == total_to_process:
                po.save(str(po_path))

            if self.delay > 0:
                time.sleep(self.delay)

        # Final save of the file
        po.save(str(po_path))
        return stats
