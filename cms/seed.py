"""Idempotent seeding helpers for initial Wagtail CMS pages and blog content."""

from __future__ import annotations

from datetime import date
from typing import Any

from wagtail.models import Page, Site

from cms.models import BlogCategory, BlogIndexPage, BlogPage, StandardPage

_STANDARD_PAGE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "slug": "home",
        "title": "Home",
        "intro": "Improved production levels with modular enterprise robotics and software.",
        "body": [
            (
                "hero",
                {
                    "heading": "Enterprise Robotics & Automation",
                    "subheading": "Unified modular web services, analytics, and intelligent automation.",
                    "cta_text": "Explore Services",
                    "cta_url": "/services/",
                },
            ),
            (
                "features",
                {
                    "heading": "Core Platform Capabilities",
                    "features": [
                        {
                            "icon": "fa-cogs",
                            "title": "Modular Architecture",
                            "description": "Composable Django and Wagtail modules built for scale.",
                        },
                        {
                            "icon": "fa-globe",
                            "title": "Multilingual Ready",
                            "description": "Localized content and navigation across six languages.",
                        },
                    ],
                },
            ),
            (
                "cta",
                {
                    "heading": "Ready to modernize your operations?",
                    "body": "Connect with our engineering team to schedule a tailored walkthrough.",
                    "button_text": "Contact Us",
                    "button_url": "/contact/",
                },
            ),
        ],
    },
    {
        "slug": "about",
        "title": "About Us",
        "intro": "Empowering modern web services, automation, and intelligent tools.",
        "body": [
            (
                "richtext",
                {
                    "heading": "Enterprise Grade Innovation",
                    "body": "<p>Our platform unites modular web applications into a unified enterprise interface.</p>",
                },
            ),
            (
                "features",
                {
                    "heading": "Engineering Principles",
                    "features": [
                        {
                            "icon": "fa-shield",
                            "title": "Enterprise Security",
                            "description": "OWASP-aligned controls, CSRF protection, and isolated config.",
                        },
                    ],
                },
            ),
        ],
    },
    {
        "slug": "services",
        "title": "Services",
        "intro": "End-to-end robotics integration, custom software, and managed operations.",
        "body": [
            (
                "hero",
                {
                    "heading": "Professional Enterprise Services",
                    "subheading": "Architecture, deployment, and continuous optimization.",
                    "cta_text": "Request Consultation",
                    "cta_url": "/contact/",
                },
            ),
            (
                "features",
                {
                    "heading": "Service Offerings",
                    "features": [
                        {
                            "icon": "fa-rocket",
                            "title": "Rapid Integration",
                            "description": "Seamless onboarding with existing ERP and CRM pipelines.",
                        },
                    ],
                },
            ),
        ],
    },
    {
        "slug": "products",
        "title": "Products",
        "intro": "Precision robotics hardware paired with real-time telemetry software.",
        "body": [
            (
                "features",
                {
                    "heading": "Featured Robotics Lineup",
                    "features": [
                        {
                            "icon": "fa-cube",
                            "title": "The Upper Eye",
                            "description": "Computer-vision inspection unit for automated quality assurance.",
                        },
                        {
                            "icon": "fa-cubes",
                            "title": "The Crab Wheel",
                            "description": "Omnidirectional industrial mobility platform.",
                        },
                    ],
                },
            ),
            (
                "cta",
                {
                    "heading": "Need custom hardware specs?",
                    "body": "Speak with our product specialists.",
                    "button_text": "Get in Touch",
                    "button_url": "/contact/",
                },
            ),
        ],
    },
    {
        "slug": "contact",
        "title": "Contact",
        "intro": "Reach our enterprise sales and support teams worldwide.",
        "body": [
            (
                "richtext",
                {
                    "heading": "Connect With Us",
                    "body": "<p>Submit an inquiry through our contact portal or reach out to our regional offices.</p>",
                },
            ),
            (
                "cta",
                {
                    "heading": "Direct Contact Form",
                    "body": "Use our legacy contact intake to route inquiries directly to CRM.",
                    "button_text": "Open Contact Form",
                    "button_url": "/contact/",
                },
            ),
        ],
    },
)


def _get_or_create_default_root() -> Page:
    """Return the default Wagtail Site root page, creating one if absent."""
    site = Site.objects.filter(is_default_site=True).first()
    if site is not None:
        return site.root_page
    root = Page.get_first_root_node() or Page.add_root(title="Root", slug="root")
    Site.objects.create(
        hostname="localhost",
        port=80,
        root_page=root,
        is_default_site=True,
        site_name="Enterprise Website",
    )
    return root


def _ensure_standard_page(root: Page, spec: dict[str, Any]) -> tuple[StandardPage, bool]:
    """Create and publish a StandardPage under root if not already present."""
    existing = StandardPage.objects.child_of(root).filter(slug=spec["slug"]).first()
    if existing is not None:
        return existing, False
    page = StandardPage(
        title=spec["title"],
        slug=spec["slug"],
        intro=spec["intro"],
        body=spec["body"],
        show_in_menus=True,
    )
    root.add_child(instance=page)
    page.save_revision().publish()
    return page, True


def _ensure_blog_index(root: Page) -> tuple[BlogIndexPage, bool]:
    """Create and publish the root BlogIndexPage if not already present."""
    blog_index = BlogIndexPage.objects.child_of(root).filter(slug="blog").first()
    if blog_index is not None:
        return blog_index, False
    blog_index = BlogIndexPage(
        title="Blog",
        slug="blog",
        intro="<p>Latest enterprise insights and engineering updates.</p>",
        show_in_menus=True,
    )
    root.add_child(instance=blog_index)
    blog_index.save_revision().publish()
    return blog_index, True


def _ensure_sample_blog_post(blog_index: BlogIndexPage) -> tuple[BlogPage, bool]:
    """Create and publish a sample BlogPage and BlogCategory if absent."""
    category, _ = BlogCategory.objects.get_or_create(
        slug="engineering",
        defaults={"name": "Engineering"},
    )
    existing = BlogPage.objects.child_of(blog_index).filter(slug="welcome-to-enterprise-cms").first()
    if existing is not None:
        return existing, False
    post = BlogPage(
        title="Welcome to Enterprise CMS",
        slug="welcome-to-enterprise-cms",
        date=date.today(),
        intro="Introducing our hybrid Wagtail CMS and multilingual blog engine.",
        body=[("richtext", {"heading": "Composable Publishing", "body": "<p>Editorial teams can now compose multi-theme pages with StreamField blocks.</p>"})],
    )
    blog_index.add_child(instance=post)
    post.categories.add(category)
    post.save_revision().publish()
    return post, True


def _ensure_blog_seed(root: Page) -> tuple[BlogIndexPage, BlogPage, int]:
    """Create and publish BlogIndexPage, BlogCategory, and a sample BlogPage."""
    blog_index, index_created = _ensure_blog_index(root)
    sample_post, post_created = _ensure_sample_blog_post(blog_index)
    return blog_index, sample_post, int(index_created) + int(post_created)


def seed_initial_cms_pages() -> dict[str, int]:
    """Idempotently seed initial StandardPages, BlogIndexPage, and a sample BlogPage."""
    root = _get_or_create_default_root()
    created = 0
    existing = 0

    for spec in _STANDARD_PAGE_SPECS:
        _, was_created = _ensure_standard_page(root, spec)
        if was_created:
            created += 1
        else:
            existing += 1

    _, _, blog_created = _ensure_blog_seed(root)
    created += blog_created
    existing += 2 - blog_created

    return {"created": created, "existing": existing}
