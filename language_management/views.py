from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from utils import get_referer_view


class LangView(TemplateView):
    template_name = "language_management/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Language Management"
        # context['redirect_to'] = get_referer_view(self.request)
        return context
