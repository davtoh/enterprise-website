from django.views.generic.base import TemplateView
from django.utils.translation import gettext_lazy as _


class LangView(TemplateView):
    template_name = "language_management/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Language Management")
        return context
