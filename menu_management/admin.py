from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Menu, MenuItem
from .sync import sync_plugin_menus


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1
    fields = ('title', 'url_name', 'url_path', 'parent', 'order', 'is_visible', 'requires_auth', 'requires_staff', 'icon')
    fk_name = 'menu'


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'item_count')
    search_fields = ('title', 'slug')
    actions = ['sync_from_plugins']
    inlines = [MenuItemInline]

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = _('Items')

    @admin.action(description=_('Sync discovered plugins into this menu'))
    def sync_from_plugins(self, request, queryset):
        for menu in queryset:
            sync_plugin_menus(menu.slug)
        self.message_user(request, _('Successfully synced plugin menu items.'))


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'menu', 'parent', 'order', 'is_visible', 'plugin_source', 'is_custom')
    list_filter = ('menu', 'is_visible', 'is_custom', 'plugin_source')
    search_fields = ('title', 'url_name', 'url_path')
    list_editable = ('order', 'is_visible')
    ordering = ('menu', 'order', 'id')
