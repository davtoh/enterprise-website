from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView as _LoginView, LogoutView as _LogoutView
#from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth import login
from django.conf import settings
try:
    from django.utils.encoding import force_str
except ImportError:
    from django.utils.encoding import force_text as force_str
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import States, Cities
from .forms import SiteUserCreationForm, ImageUploadForm


from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.utils.translation import gettext as _


# https://simpleisbetterthancomplex.com/tutorial/2018/01/29/how-to-implement-dependent-or-chained-dropdown-list-with-django.html
# https://django-easy-tutorial.blogspot.com/2017/04/django-send-one-time-use-activation-email.html


def send_account_activation_email(request, user):
    text_content = 'Account Activation Email'
    subject = 'Email Activation'
    template_name = "emails/user_management/activation.html"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipients = [user.email]
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    if isinstance(uidb64, bytes):
        uidb64 = uidb64.decode()
    kwargs = {
        "uidb64": uidb64,
        "token": default_token_generator.make_token(user)
    }
    activation_url = reverse("user_management:activate_user_account", kwargs=kwargs)

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
    UserModel = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))  # https://stackoverflow.com/a/47924973
        user = UserModel.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
        user = None
    if user and default_token_generator.check_token(user, token):
        user.is_email_verified = True
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, _("Welcome, %(username)s! Your account has been successfully activated.") % {'username': user.username})
        return redirect('user_management:profile')
    else:
        messages.error(request, _("The activation link is invalid or has expired. Please log in or request a new activation."))
        return redirect('user_management:login')


class LoginView(_LoginView):
    template_name = 'user_management/login.html'
    authentication_form = None

    def form_valid(self, form):
        user = form.get_user()
        messages.success(self.request, _("Welcome back, %(name)s!") % {'name': user.first_name or user.username})
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Invalid username or password. Please check your credentials and try again."))
        return super().form_invalid(form)


class LogoutView(_LogoutView):
    template_name = 'user_management/logout.html'
    http_method_names = ['get', 'post', 'options']

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, _("You have been successfully logged out. See you soon!"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Allow graceful GET logout while supporting Django 5 POST standards
        auth_logout(request)
        return render(request, self.template_name)


class SiteUserListView(LoginRequiredMixin, ListView):
    model = get_user_model()
    context_object_name = 'Users'
    template_name = 'user_management/siteuser_list.html'


class SignUpView(CreateView):
    """
    View the signup page with all the fields with signup.html template
    """
    model = get_user_model()
    form_class = SiteUserCreationForm
    template_name = 'user_management/signup.html'
    success_url = reverse_lazy('user_management:login')

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        # form.send_email()  # intended to send mail
        response = super().form_valid(form)
        messages.success(self.request, _("Account created successfully! You can now log in."))
        return response

    def form_invalid(self, form):
        messages.error(self.request, _("Please correct the errors below to complete your registration."))
        return super().form_invalid(form)


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


class SiteUserUpdateView(LoginRequiredMixin, UpdateView):
    model = get_user_model()
    fields = ('first_name', 'last_name', 'email', 'birthdate', 'country', 'city')
    template_name = 'user_management/signup.html'
    success_url = reverse_lazy('user_management:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _("Your profile has been updated successfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Unable to save profile changes. Please review the highlighted fields."))
        return super().form_invalid(form)


class SiteUserProfileView(LoginRequiredMixin, DetailView):
    model = get_user_model()
    template_name = 'user_management/profile.html'
    context_object_name = 'object'

    def get_object(self, queryset=None):
        return self.request.user


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

