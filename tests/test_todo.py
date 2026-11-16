import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from todo.models import Todo

User = get_user_model()


@pytest.fixture
def sample_todo(db):
    return Todo.objects.create(
        title="Complete Quarterly Audit",
        text="Review all expense reports and verify transaction IDs.",
    )


@pytest.mark.django_db
class TestTodoApp:
    """Tests for Todo task management application."""

    def test_todo_list_empty(self, client):
        response = client.get(reverse("todo:index"))
        assert response.status_code == 200
        assert "No tasks yet" in response.content.decode()

    def test_todo_list_with_items(self, client, sample_todo):
        response = client.get(reverse("todo:index"))
        assert response.status_code == 200
        assert sample_todo.title in response.content.decode()

    def test_todo_list_authenticated_greeting(self, client):
        user = User.objects.create_user(username="todo_user", password="Pass123!Password")
        client.force_login(user)
        response = client.get(reverse("todo:index"))
        assert response.status_code == 200
        assert "Welcome, todo_user!" in response.content.decode()

    def test_todo_add_get(self, client):
        response = client.get(reverse("todo:add"))
        assert response.status_code == 200

    def test_todo_add_post_success(self, client):
        url = reverse("todo:add")
        data = {
            "title": "Prepare Board Deck",
            "text": "Finalize Q3 strategic slides.",
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        assert Todo.objects.filter(title="Prepare Board Deck").exists()
        messages = list(response.context["messages"])
        assert any("Task created successfully" in str(m) for m in messages)

    def test_todo_add_post_validation_error(self, client):
        url = reverse("todo:add")
        # Empty title
        data = {
            "title": "",
            "text": "Some text without title",
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert not Todo.objects.filter(text="Some text without title").exists()

    def test_todo_details_success(self, client, sample_todo):
        url = reverse("todo:details", kwargs={"id": sample_todo.id})
        response = client.get(url)
        assert response.status_code == 200
        assert sample_todo.title in response.content.decode()
        assert sample_todo.text in response.content.decode()

    def test_todo_details_with_session_timezone(self, client, sample_todo):
        session = client.session
        session["django_timezone"] = "America/Bogota"
        session.save()

        url = reverse("todo:details", kwargs={"id": sample_todo.id})
        response = client.get(url)
        assert response.status_code == 200
        assert "America/Bogota" in response.content.decode()

    def test_todo_details_not_found(self, client):
        url = reverse("todo:details", kwargs={"id": 99999})
        response = client.get(url)
        assert response.status_code == 404

    def test_todo_delete_success(self, client, sample_todo):
        url = reverse("todo:delete", kwargs={"id": sample_todo.id})
        response = client.post(url, follow=True)
        assert response.status_code == 200
        assert not Todo.objects.filter(id=sample_todo.id).exists()

    def test_todo_delete_not_found(self, client):
        url = reverse("todo:delete", kwargs={"id": 99999})
        response = client.post(url)
        assert response.status_code == 404

    def test_action_item_alias_and_defaults(self, db):
        from todo.models import ActionItem, ActionItemStatus

        assert ActionItem is Todo
        item = ActionItem.objects.create(title="Legacy Call", text="Only title and text")
        assert item.status == ActionItemStatus.PENDING
        assert item.owner is None
        assert item.due_date is None
        assert item.content_object is None

    def test_action_item_generic_foreign_key_linkage(self, db):
        from crm.models import Contact, Lead
        from erp.models import Invoice
        from intelligent_tracker_hub.models import SecurityEvent
        from todo.models import ActionItem

        contact = Contact.objects.create(first_name="Ada", last_name="Lovelace", email="ada@example.com")
        lead = Lead.objects.create(title="Enterprise Deal", contact=contact)
        invoice = Invoice.objects.create(invoice_number="INV-4001", customer_name="Analytical Engine Co")
        event = SecurityEvent.objects.create(camera_id="cam-north-01")

        lead_item = ActionItem.objects.create(title="Call Lead", text="Follow up", content_object=lead)
        inv_item = ActionItem.objects.create(title="Collect Invoice", text="Send reminder", content_object=invoice)
        sec_item = ActionItem.objects.create(title="Review Alert", text="Inspect clip", content_object=event)

        lead_item.refresh_from_db()
        inv_item.refresh_from_db()
        sec_item.refresh_from_db()

        assert lead_item.content_object == lead
        assert inv_item.content_object == invoice
        assert sec_item.content_object == event

    def test_todo_add_with_status_due_date_and_owner_filter(self, client):
        import datetime
        from todo.models import ActionItemStatus

        user = User.objects.create_user(username="action_owner", password="Pass123!Password")
        client.force_login(user)

        response = client.post(
            reverse("todo:add"),
            {
                "title": "Quarterly Review",
                "text": "Prepare action items",
                "status": ActionItemStatus.IN_PROGRESS,
                "due_date": "2026-12-01",
            },
            follow=True,
        )
        assert response.status_code == 200
        item = Todo.objects.get(title="Quarterly Review")
        assert item.owner == user
        assert item.status == ActionItemStatus.IN_PROGRESS
        assert item.due_date == datetime.date(2026, 12, 1)

        filtered = client.get(reverse("todo:index"), {"status": ActionItemStatus.IN_PROGRESS, "owner": "me"})
        assert filtered.status_code == 200
        assert "Quarterly Review" in filtered.content.decode()

        detail_res = client.get(reverse("todo:details", kwargs={"id": item.id}))
        assert detail_res.status_code == 200
        assert "action_owner" in detail_res.content.decode()

    def test_todo_plugin_templates_preserved(self):
        from todo.plugin import TodoPlugin

        assert TodoPlugin.plugin_templates == {
            "bootstrap5": "todo/bs5/",
            "tailwind": "todo/tw/",
        }
