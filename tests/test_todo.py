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
