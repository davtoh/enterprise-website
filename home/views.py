from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView

from .services import ingest_website_contact_submission


def _get_seeded_cms_page(slug: str):
    """Return the live seeded StandardPage for a legacy home slug, if present."""
    from cms.models import StandardPage

    return StandardPage.objects.live().filter(slug=slug).first()


class HomeView(TemplateView):
    # https://github.com/harukaeru/Brython-Django
    template_name = "home/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Home - Enterprise Website"
        context['banner_content_title'] = "Enterprise Website"
        context['cms_page'] = _get_seeded_cms_page("home")
        return context


class AboutView(TemplateView):
    template_name = "home/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "About Us - Enterprise Website"
        context['cms_page'] = _get_seeded_cms_page("about")
        return context


class ServicesView(TemplateView):
    template_name = "home/services.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Services - Enterprise Website"
        context['cms_page'] = _get_seeded_cms_page("services")
        return context


class ProductsView(TemplateView):
    template_name = "home/products.html"

    def get_context_data(self, **kwargs):
        from erp.models import Product

        context = super().get_context_data(**kwargs)
        context['title'] = "Products - Enterprise Website"
        context['cms_page'] = _get_seeded_cms_page("products")
        context['products'] = list(
            Product.objects.filter(is_active=True, is_published=True)
            .select_related("category")
            .order_by("name")
        )
        return context


class ContactView(TemplateView):
    template_name = "home/contact.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Contact Us - Enterprise Website"
        context['cms_page'] = _get_seeded_cms_page("contact")
        return context

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        if name and email and message:
            ingest_website_contact_submission(
                name=name,
                email=email,
                subject=subject,
                message=message,
            )
            messages.success(request, _("Thank you, %(name)s! Your message has been received.") % {'name': name})
        else:
            messages.error(request, _("Please fill out all required fields."))
        return redirect('home:contact')


home = HomeView.as_view()
about = AboutView.as_view()
services = ServicesView.as_view()
products = ProductsView.as_view()
contact = ContactView.as_view()

#def index(request):
#    return render(request, 'brython/index.html')