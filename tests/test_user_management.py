import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from user_management.views import send_account_activation_email

User = get_user_model()


@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="ValidPassword123!",
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    return user


@pytest.mark.django_db
class TestUserAuthentication:
    """Tests for user signup, login, logout, and activation."""

    def test_signup_get(self, client):
        response = client.get(reverse("user_management:signup"))
        assert response.status_code == 200

    def test_signup_post_success(self, client):
        url = reverse("user_management:signup")
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "ComplexPass1234!",
            "password2": "ComplexPass1234!",
            "first_name": "New",
            "last_name": "Person",
            "birthdate": "1995-05-15",
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        assert User.objects.filter(username="newuser").exists()

    def test_signup_post_invalid(self, client):
        url = reverse("user_management:signup")
        # Missing passwords
        data = {
            "username": "baduser",
            "email": "bad@example.com",
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert not User.objects.filter(username="baduser").exists()

    def test_login_valid_credentials(self, client, test_user):
        url = reverse("user_management:login")
        response = client.post(url, {"username": "testuser", "password": "ValidPassword123!"})
        assert response.status_code == 302
        # Follow to profile/success
        response = client.get(reverse("user_management:profile"))
        assert response.status_code == 200

    def test_login_invalid_credentials(self, client, test_user):
        url = reverse("user_management:login")
        response = client.post(url, {"username": "testuser", "password": "WrongPassword!"})
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) > 0

    def test_logout_get_and_post(self, client, test_user):
        client.login(username="testuser", password="ValidPassword123!")
        
        # Test GET logout
        response = client.get(reverse("user_management:logout"))
        assert response.status_code == 200

        # Login again and test POST logout
        client.login(username="testuser", password="ValidPassword123!")
        response = client.post(reverse("user_management:logout"))
        assert response.status_code in (200, 302)

    def test_profile_requires_login(self, client):
        url = reverse("user_management:profile")
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login" in response.url

    def test_profile_authenticated_access(self, client, test_user):
        client.force_login(test_user)
        url = reverse("user_management:profile")
        response = client.get(url)
        assert response.status_code == 200
        assert test_user.username in response.content.decode()

    def test_profile_update(self, client, test_user):
        client.force_login(test_user)
        url = reverse("user_management:update", kwargs={"pk": test_user.pk})
        data = {
            "first_name": "UpdatedName",
            "last_name": "UpdatedLast",
            "email": "updated@example.com",
            "birthdate": "1990-01-01",
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        test_user.refresh_from_db()
        assert test_user.first_name == "UpdatedName"
        assert test_user.email == "updated@example.com"

    def test_account_activation_flow(self, client, rf):
        user = User.objects.create_user(
            username="inactive_user",
            email="inactive@example.com",
            password="SomePassword123!",
            is_active=False,
        )

        # Generate activation tokens
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Trigger activation link
        activate_url = reverse(
            "user_management:activate_user_account",
            kwargs={"uidb64": uidb64, "token": token},
        )
        response = client.get(activate_url, follow=True)
        assert response.status_code == 200

        user.refresh_from_db()
        assert user.is_active is True


    def test_account_activation_invalid_token(self, client):
        activate_url = reverse(
            "user_management:activate_user_account",
            kwargs={"uidb64": "invalid-uid", "token": "invalid-token"},
        )
        response = client.get(activate_url, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) > 0

    def test_send_account_activation_email(self, rf, test_user):
        request = rf.get("/")
        send_account_activation_email(request, test_user)

    def test_ajax_load_states_and_cities(self, client):
        response = client.get(reverse("user_management:ajax_load_states"), {"country": 1})
        assert response.status_code == 200

        response = client.get(reverse("user_management:ajax_load_cities"), {"country": 1, "state": 1})
        assert response.status_code == 200

    def test_populate_users_command_test_flag(self):
        from django.core.management import call_command
        call_command("populate_users", test=True)
        assert User.objects.filter(username="superuser").exists()
        assert User.objects.filter(username="staff").exists()
        assert User.objects.filter(username="regular").exists()

        # Test update flag
        call_command("populate_users", test=True, update=True)

    def test_populate_users_command_manual_flags(self):
        from django.core.management import call_command
        call_command("populate_users", superuser=["admin_test"], staff=["staff_test"], regular=["user_test"])
        assert User.objects.filter(username="admin_test").exists()
        assert User.objects.filter(username="staff_test").exists()
        assert User.objects.filter(username="user_test").exists()

    def test_site_user_creation_form_birthdate_validation(self):
        import datetime
        from django.core.exceptions import ValidationError
        from user_management.forms import SiteUserCreationForm
        form = SiteUserCreationForm()

        # Future date
        form.cleaned_data = {"birthdate": datetime.date.today() + datetime.timedelta(days=1)}
        with pytest.raises(ValidationError):
            form.clean_birthdate()

        # Less than legal age
        form.cleaned_data = {"birthdate": datetime.date.today() - datetime.timedelta(days=365 * 5)}
        with pytest.raises(ValidationError):
            form.clean_birthdate()

        # Valid age
        valid_date = datetime.date.today() - datetime.timedelta(days=365 * 25)
        form.cleaned_data = {"birthdate": valid_date}
        assert form.clean_birthdate() == valid_date

    def test_user_management_and_location_models_str(self):
        from user_management.models import Gender
        from location_management.models import Countries, States, Cities
        from timezone_management.models import TimeZone

        gender = Gender.objects.create(gender="Non-Binary")
        assert str(gender) == "Non-Binary"

        country = Countries.objects.create(name="Fictional Land", code="FL")
        assert str(country) == "Fictional Land"

        state = States.objects.create(name="Capital Region", code="CR", country=country)
        assert str(state) == "Capital Region"

        city = Cities.objects.create(
            name="Capital City",
            country=country,
            state=state,
            latitude=10.12345678,
            longitude=-75.12345678,
        )
        assert str(city) == "Capital City"

        tz = TimeZone.objects.create(timezone="UTC")
        assert tz.timezone == "UTC"

    def test_process_timezone_signal_receiver(self, test_user):
        from user_management.models import process_timezone
        from timezone_management.models import TimeZone

        # Anonymous user (no timezone attribute)
        class Anon:
            pass
        process_timezone(sender=None, instance=Anon(), timezone="UTC")

        # User with timezone set
        tz = TimeZone.objects.create(timezone="America/Bogota")
        test_user.timezone = tz
        test_user.save()
        process_timezone(sender=None, instance=test_user, timezone="America/Bogota")




