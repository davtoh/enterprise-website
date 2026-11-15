from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView


class HomeView(TemplateView):
    # https://github.com/harukaeru/Brython-Django
    template_name = "webprogram/brython/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Brython WebProgram")
        return context


index = HomeView.as_view()