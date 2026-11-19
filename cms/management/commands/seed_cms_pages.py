from django.core.management.base import BaseCommand

from cms.seed import seed_initial_cms_pages


class Command(BaseCommand):
    """Seed initial Wagtail CMS pages and sample blog content idempotently."""

    help = "Seed initial Wagtail StandardPages, BlogIndexPage, and sample BlogPage."

    def handle(self, *args, **options):
        summary = seed_initial_cms_pages()
        self.stdout.write(
            self.style.SUCCESS(
                f"CMS seeding complete: created={summary['created']}, existing={summary['existing']}"
            )
        )
