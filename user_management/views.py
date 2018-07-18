from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.views import LoginView as _LoginView, LogoutView as _LogoutView
#from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import SiteUser, Countries, States, Cities
from .forms import SiteUserCreationForm, ImageUploadForm
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth import login
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_encode
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string


# https://simpleisbetterthancomplex.com/tutorial/2018/01/29/how-to-implement-dependent-or-chained-dropdown-list-with-django.html
# https://django-easy-tutorial.blogspot.com/2017/04/django-send-one-time-use-activation-email.html


def send_account_activation_email(request, user):
    text_content = 'Account Activation Email'
    subject = 'Email Activation'
    template_name = "emails/account/activation.html"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipients = [user.email]
    kwargs = {
        "uidb64": urlsafe_base64_encode(force_bytes(user.pk)).decode(),
        "token": default_token_generator.make_token(user)
    }
    activation_url = reverse("app:activate_user_account", kwargs=kwargs)

    activate_url = "{0}://{1}{2}".format(request.scheme, request.get_host(), activation_url)

    context = {
        'user': user,
        'activate_url': activate_url
    }
    html_content = render_to_string(template_name, context)
    email = EmailMultiAlternatives(subject, text_content, from_email, recipients)
    email.attach_alternative(html_content, "text/html")
    email.send()


def activate_user_account(request, uidb64=None, token=None):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = SiteUser.objects.get(pk=uid)
    except SiteUser.DoesNotExist:
        user = None
    if user and default_token_generator.check_token(user, token):
        user.is_email_verified = True
        user.is_active = True
        user.save()
        login(request, user)
        return redirect('hr:user_profile')
    else:
        return HttpResponse("Activation link has expired")


class LoginView(_LoginView):
    template_name = 'user_management/login.html'
    authentication_form = None


class LogoutView(_LogoutView):
    template_name = 'user_management/logout.html'


class SiteUserListView(LoginRequiredMixin, ListView):
    model = SiteUser
    context_object_name = 'Users'


class SignUpView(CreateView):
    """
    View the signup page with all the fields with signup.html template
    """
    model = SiteUser
    form_class = SiteUserCreationForm
    template_name = 'user_management/signup.html'
    success_url = reverse_lazy('user_management:login')


def load_states(request):
    """
    loads the states for the given country id using the GET method

    :param request: with 'country' in  GET method
    :return: rendered state_dropdown_list_options.html with context: 'states'
    """
    country_id = request.GET.get('country')
    states = States.objects.filter(country_id=country_id).order_by('name')
    return render(request, 'user_management/state_dropdown_list_options.html', {'states': states})


def load_cities(request):
    """
    loads the cities for the given state and country ids using the GET method

    :param request: with 'country', 'state' in  GET method
    :return: rendered city_dropdown_list_options.html with context: 'cities'
    """
    country_id = request.GET.get('country')
    state_id = request.GET.get('state')
    cities = Cities.objects.filter(state_id=state_id, country_id=country_id).order_by('name')
    return render(request, 'user_management/city_dropdown_list_options.html', {'cities': cities})


class SiteUserUpdateView(UpdateView):
    model = SiteUser
    fields = ('username', 'first_name', 'last_name', 'email', 'birthdate', 'country', 'city', 'password')
    success_url = reverse_lazy('user_management:login')


class SiteUserProfileView(DetailView):
    model = SiteUser
    fields = ('username', 'first_name', 'last_name', 'email', 'birthdate', 'country', 'city', 'password')


def upload_pic(request):
    # https://coderwall.com/p/bz0sng/simple-django-image-upload-to-model-imagefield
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            m = request
            m.model_pic = form.cleaned_data['image']
            m.save()
            return HttpResponse('image upload success')
    else:
        return render(request, 'user_management/upload_image_form.html')
    return HttpResponseForbidden('allowed only via POST')

