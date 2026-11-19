from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalManyToManyField
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page, TranslatableMixin
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from .blocks import CMSStreamBlock


@register_snippet
class BlogCategory(TranslatableMixin, models.Model):
    """Translatable blog category snippet for organizing BlogPage entries."""

    name = models.CharField(_("Name"), max_length=100)
    slug = models.SlugField(_("Slug"), max_length=100)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = _("Blog Category")
        verbose_name_plural = _("Blog Categories")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class StandardPage(Page):
    """Flexible CMS page composed of theme-aware StreamField blocks."""

    intro = models.CharField(_("Introduction"), max_length=255, blank=True)
    body = StreamField(
        CMSStreamBlock(),
        verbose_name=_("Body"),
        blank=True,
        use_json_field=True,
    )

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    template = "cms/standard_page.html"

    class Meta:
        verbose_name = _("Standard Page")
        verbose_name_plural = _("Standard Pages")


class BlogIndexPage(Page):
    """Landing page listing published BlogPage children with optional category filtering."""

    intro = RichTextField(_("Introduction"), blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["cms.BlogPage"]
    template = "cms/blog_index_page.html"

    class Meta:
        verbose_name = _("Blog Index Page")
        verbose_name_plural = _("Blog Index Pages")

    def get_context(self, request, *args, **kwargs):
        """Return live child blog posts ordered newest-first, filtered by category if requested."""
        context = super().get_context(request, *args, **kwargs)
        posts = BlogPage.objects.child_of(self).live().public().order_by("-date", "-first_published_at")
        category_slug = request.GET.get("category", "").strip()
        if category_slug:
            posts = posts.filter(categories__slug=category_slug)
        context["posts"] = posts
        context["active_category"] = category_slug
        context["categories"] = BlogCategory.objects.filter(locale=self.locale)
        return context


class BlogPage(Page):
    """Individual enterprise blog post with StreamField content, date, image, and categories."""

    date = models.DateField(_("Post date"))
    intro = models.CharField(_("Summary"), max_length=255, blank=True)
    body = StreamField(
        CMSStreamBlock(),
        verbose_name=_("Body"),
        blank=True,
        use_json_field=True,
    )
    categories = ParentalManyToManyField(
        "cms.BlogCategory",
        verbose_name=_("Categories"),
        blank=True,
    )
    feed_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Featured Image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("date"),
        FieldPanel("intro"),
        FieldPanel("feed_image"),
        FieldPanel("categories", widget=forms.CheckboxSelectMultiple),
        FieldPanel("body"),
    ]

    parent_page_types = ["cms.BlogIndexPage"]
    template = "cms/blog_page.html"

    class Meta:
        verbose_name = _("Blog Page")
        verbose_name_plural = _("Blog Pages")
