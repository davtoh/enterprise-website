from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model

from crm.models import Company, Contact, Lead, LeadStage, LeadSource

User = get_user_model()


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(
        username="crm_agent",
        email="crm_agent@example.com",
        password="ValidPassword123!",
        is_staff=True,
    )


@pytest.fixture
def test_company(db):
    return Company.objects.create(
        name="Acme Corp",
        industry="Technology",
        website="https://acme.example.com",
        city="Austin",
        country="US",
        annual_revenue=Decimal("1500000.00"),
    )


@pytest.fixture
def test_contact(db, test_company):
    return Contact.objects.create(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+1555123456",
        company=test_company,
        job_title="VP of Sales",
        tags="enterprise, vip",
        is_subscribed=True,
    )


@pytest.fixture
def test_lead(db, test_contact, test_company, auth_user):
    return Lead.objects.create(
        title="Acme Cloud Platform Expansion",
        contact=test_contact,
        company=test_company,
        stage=LeadStage.NEW,
        source=LeadSource.WEBSITE,
        value=Decimal("45000.00"),
        assigned_to=auth_user,
    )

