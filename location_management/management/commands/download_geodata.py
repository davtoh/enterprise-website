"""
Management command to download the world.sql geodata file on-demand.

Original source references:
https://github.com/prograhammer/countries-regions-cities
https://www.geodatasource.com/world-cities-database/free
"""

import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import requests

DEFAULT_GEODATA_URL = os.getenv(
    "GEODATA_DOWNLOAD_URL",
    "https://raw.githubusercontent.com/prograhammer/countries-regions-cities/master/world.sql",
)


class Command(BaseCommand):
    help = (
        "Downloads the world.sql geodata file from upstream repository or archive. "
        "Keeps the large 175MB geodata file out of Git repositories."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default=DEFAULT_GEODATA_URL,
            help=f"Download URL for world.sql (default: {DEFAULT_GEODATA_URL})",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Target output file path (default: <BASE_DIR>/world.sql)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite destination file if it already exists",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=65536,
            help="Streaming download chunk size in bytes (default: 65536)",
        )

    def handle(self, *args, **options):
        url = options["url"]
        output_arg = options["output"]
        force = options["force"]
        chunk_size = options["chunk_size"]

        dest_path = Path(output_arg) if output_arg else settings.BASE_DIR / "world.sql"
        temp_path = dest_path.with_suffix(".sql.tmp")

        if dest_path.exists() and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"Geodata file already exists at {dest_path}. "
                    "Use --force to overwrite."
                )
            )
            return

        self.stdout.write(self.style.NOTICE(f"Connecting to {url} ..."))

        try:
            with requests.get(url, stream=True, timeout=60) as response:
                if response.status_code != 200:
                    raise CommandError(
                        f"Failed to download geodata: HTTP {response.status_code} {response.reason}"
                    )

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                mb_done = downloaded / (1024 * 1024)
                                mb_total = total_size / (1024 * 1024)
                                self.stdout.write(
                                    f"\rDownloading: {percent:5.1f}% ({mb_done:.1f}/{mb_total:.1f} MB)",
                                    ending="",
                                )
                            else:
                                mb_done = downloaded / (1024 * 1024)
                                self.stdout.write(
                                    f"\rDownloaded: {mb_done:.1f} MB", ending=""
                                )

                # Replace destination atomically
                if temp_path.exists():
                    if dest_path.exists():
                        dest_path.unlink()
                    temp_path.rename(dest_path)

            self.stdout.write("")  # Newline after carriage return progress
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully downloaded geodata to {dest_path} ({downloaded / (1024 * 1024):.1f} MB)"
                )
            )
            self.stdout.write(
                "You can now run 'python manage.py populate_locations' to load it into the database."
            )

        except requests.RequestException as exc:
            if temp_path.exists():
                temp_path.unlink()
            raise CommandError(f"Network error while downloading geodata: {exc}")
        except Exception as exc:
            if temp_path.exists():
                temp_path.unlink()
            raise CommandError(f"Unexpected error: {exc}")
