from plugin_registry import AppPlugin, MenuItemDefinition
from django.utils.translation import gettext_lazy as _


class HomePlugin(AppPlugin):
    name = "home"
    verbose_name = _("Corporate Showcase")
    description = _("Corporate showcase pages: Home, About, Services, Products, Contact")
    category = "core"
    
    menu_items = [
        MenuItemDefinition(label=_("Home"), url_name="home:index", order=10),
        MenuItemDefinition(label=_("About Us"), url_name="home:about", order=20),
        MenuItemDefinition(label=_("Services"), url_name="home:services", order=30),
        MenuItemDefinition(label=_("Products"), url_name="home:products", order=40),
        MenuItemDefinition(label=_("Contact"), url_name="home:contact", order=50),
    ]
