from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.views import LoginView as _LoginView, LogoutView as _LogoutView
#from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import SiteUser
from .forms import SiteUserCreationForm

# https://simpleisbetterthancomplex.com/tutorial/2018/01/29/how-to-implement-dependent-or-chained-dropdown-list-with-django.html


class LoginView(_LoginView):
    template_name = 'user_management/login.html'
    authentication_form = None


class LogoutView(_LogoutView):
    template_name = 'user_management/logout.html'


class SiteUserListView(LoginRequiredMixin, ListView):
    model = SiteUser
    context_object_name = 'Users'


class SignUpView(CreateView):
    model = SiteUser
    fields = ('username', 'first_name', 'last_name', 'email', 'birthdate', 'country', 'city', 'password')
    success_url = reverse_lazy('login')


class SignUp(CreateView):
    form_class = SiteUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'signup.html'


class SiteUserUpdateView(UpdateView):
    model = SiteUser
    fields = ('username', 'first_name', 'last_name', 'email', 'birthdate', 'country', 'city', 'password')
    success_url = reverse_lazy('login')


class SiteUserProfileView(DetailView):
    model = SiteUser
    fields = ('username', 'first_name', 'last_name', 'email', 'birthdate', 'country', 'city', 'password')
