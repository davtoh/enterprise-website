from django.conf import settings
from django.utils.translation import check_for_language, gettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.i18n import set_language


class LangView(TemplateView):
    template_name = "language_management/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Language Management")
        return context


def set_language_and_sync_profile(request):
    """Delegate to Django's set_language view and persist preferred_language for authenticated users."""
    response = set_language(request)
    if request.method == "POST" and getattr(request, "user", None) and request.user.is_authenticated:
        lang_code = request.POST.get("language", "").strip()
        supported_codes = {code for code, _label in settings.LANGUAGES}
        if lang_code and lang_code in supported_codes and check_for_language(lang_code):
            if getattr(request.user, "preferred_language", "") != lang_code:
                request.user.preferred_language = lang_code
                request.user.save(update_fields=["preferred_language"])
    return response
