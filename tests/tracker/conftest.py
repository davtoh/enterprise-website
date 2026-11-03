from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from crm.models import Company, Contact, SecurityClearance
from location_management.models import Countries, States, Cities, Location

User = get_user_model()

# Valid 1x1 transparent PNG data in Base64
SAMPLE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(
        username="sec_operator",
        email="operator@example.com",
        password="ValidPassword123!",
        is_staff=True,
    )


@pytest.fixture
def test_location(db):
    country = Countries.objects.create(name="United States", code="US")
    state = States.objects.create(country=country, name="Texas", code="TX")
    city = Cities.objects.create(
        country=country,
        state=state,
        name="Austin",
        latitude=Decimal("30.2672"),
        longitude=Decimal("-97.7431"),
    )
    return Location.objects.create(
        name="North Production Campus",
        code="SITE-NORTH-01",
        city=city,
        address="1000 Industrial Parkway",
    )


@pytest.fixture
def test_company(db):
    return Company.objects.create(
        name="Cyberdyne Systems",
        industry="Autonomous Defense",
        city="Austin",
        country="United States",
    )


@pytest.fixture
def test_contacts(db, test_company, test_location):
    c1 = Contact.objects.create(
        first_name="Sarah",
        last_name="Connor",
        email="sconnor@example.com",
        company=test_company,
        security_clearance=SecurityClearance.VIP,
        license_plate="TX-999-VIP",
        security_tag="exec-zone",
        face_embedding_vector=[0.05] * 512,
    )
    c2 = Contact.objects.create(
        first_name="Kyle",
        last_name="Reese",
        email="kreese@example.com",
        company=test_company,
        security_clearance=SecurityClearance.CONTRACTOR,
        license_plate="CA-123-KLR",
        security_tag="contractor-gate",
        valid_from=timezone.now() - timezone.timedelta(days=2),
        valid_until=timezone.now() + timezone.timedelta(days=5),
    )
    c3 = Contact.objects.create(
        first_name="Expired",
        last_name="Visitor",
        email="expired@example.com",
        company=test_company,
        security_clearance=SecurityClearance.VISITOR,
        valid_from=timezone.now() - timezone.timedelta(days=10),
        valid_until=timezone.now() - timezone.timedelta(days=1),
    )
    c4 = Contact.objects.create(
        first_name="Miles",
        last_name="Dyson",
        email="mdyson@example.com",
        company=test_company,
        security_clearance=SecurityClearance.BANNED,
        license_plate="BANNED-01",
    )
    return [c1, c2, c3, c4]

