from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, NoReverseMatch


class Menu(models.Model):
    """Represents a named navigation menu location, e.g., 'main_navbar', 'footer'."""
    slug = models.SlugField(_('Slug'), unique=True, max_length=50, help_text=_('Unique identifier, e.g. main_navbar'))
    title = models.CharField(_('Title'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Is active'), default=True)

    class Meta:
        verbose_name = _('Menu')
        verbose_name_plural = _('Menus')
        ordering = ['slug']

    def __str__(self):
        return self.title


class MenuItem(models.Model):
    """
    Navigation item belonging to a Menu.
    Supports hierarchical nesting (parent-child), reverse Django URL names or raw external URLs,
    and linking to an originating AppPlugin.
    """
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='items', verbose_name=_('Menu'))
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name=_('Parent item'))
    
    title = models.CharField(_('Title'), max_length=100, help_text=_('Display label for the menu item'))
    url_name = models.CharField(_('Named URL'), max_length=150, blank=True, help_text=_('Django reverse URL name, e.g., home:about'))
    url_path = models.CharField(_('Explicit URL / Path'), max_length=255, blank=True, help_text=_('External or explicit URL, e.g., /about/ or https://...'))
    icon = models.CharField(_('Icon CSS class'), max_length=50, blank=True, help_text=_('FontAwesome or Linearicons class, e.g., fa fa-tasks'))
    
    order = models.PositiveIntegerField(_('Order'), default=100, help_text=_('Display order (lower numbers appear first)'))
    is_visible = models.BooleanField(_('Visible'), default=True, help_text=_('Toggle to hide or show this item'))
    
    # Access controls
    requires_auth = models.BooleanField(_('Requires authentication'), default=False)
    requires_staff = models.BooleanField(_('Requires staff access'), default=False)
    
    # Origin tracking for plugin discovery & synchronization
    plugin_source = models.CharField(_('Plugin source'), max_length=100, blank=True, help_text=_('Originating plugin ID, e.g., todo, polls'))
    is_custom = models.BooleanField(_('Custom user item'), default=True, help_text=_('True if created manually by admin rather than auto-discovered'))
    wagtail_page = models.ForeignKey(
        'wagtailcore.Page',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='menu_items',
        verbose_name=_('Wagtail Page'),
    )

    class Meta:
        verbose_name = _('Menu Item')
        verbose_name_plural = _('Menu Items')
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.title} ({self.get_resolved_url()})"

    def get_localized_page(self, language_code: str | None = None):
        """Return the live localized Wagtail Page for the active or given language."""
        if not self.wagtail_page_id:
            return None
        page = self.wagtail_page
        lang = language_code or translation.get_language()
        if lang and getattr(page, 'locale', None) and page.locale.language_code != lang:
            from wagtail.models import Locale

            locale = Locale.objects.filter(language_code=lang).first()
            if locale is not None:
                translated = page.get_translation_or_none(locale)
                if translated is not None and translated.live:
                    return translated
        return page if page.live else None

    def get_resolved_title(self, language_code: str | None = None) -> str:
        """Resolve localized Wagtail page title when linked, falling back to MenuItem.title."""
        if self.wagtail_page_id:
            page = self.get_localized_page(language_code=language_code)
            if page is not None:
                return page.title
        return self.title

    def get_resolved_url(self, language_code: str | None = None) -> str:
        """Resolve the URL using url_name, localized wagtail_page, or url_path."""
        if self.url_name:
            try:
                return reverse(self.url_name)
            except NoReverseMatch:
                pass
        if self.wagtail_page_id:
            page = self.get_localized_page(language_code=language_code)
            if page is not None:
                page_url = page.url
                if page_url:
                    return page_url
        return self.url_path or '#'

    def is_accessible_by(self, user) -> bool:
        """Check if given user has permission to see this menu item."""
        if not self.is_visible:
            return False
        if self.requires_staff and not getattr(user, 'is_staff', False):
            return False
        if self.requires_auth and not getattr(user, 'is_authenticated', False):
            return False
        return True
