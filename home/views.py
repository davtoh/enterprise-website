from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.views.generic.base import TemplateView


class HomeView(TemplateView):
    # https://github.com/harukaeru/Brython-Django
    template_name = "home/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Brythonを使ったやつ"
        return context


home = HomeView.as_view()
#def index(request):
#    return render(request, 'brython/index.html')