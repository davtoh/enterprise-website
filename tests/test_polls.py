import datetime
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from polls.models import Choice, Question


@pytest.fixture
def published_poll(db):
    question = Question.objects.create(
        question_text="What is your favorite cloud provider?",
        pub_date=timezone.now() - datetime.timedelta(hours=1),
        opened=True,
    )
    Choice.objects.create(question=question, choice_text="Google Cloud Platform", votes=5)
    Choice.objects.create(question=question, choice_text="Amazon Web Services", votes=3)
    Choice.objects.create(question=question, choice_text="Microsoft Azure", votes=2)
    return question


@pytest.fixture
def future_poll(db):
    return Question.objects.create(
        question_text="Will quantum computing emerge in 2035?",
        pub_date=timezone.now() + datetime.timedelta(days=30),
        opened=True,
    )


@pytest.mark.django_db
class TestPollsApp:
    """Tests for the Polls voting application."""

    def test_was_published_recently_with_past_question(self):
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59)
        recent_question = Question(pub_date=time)
        assert recent_question.was_published_recently() is True

    def test_was_published_recently_with_old_question(self):
        time = timezone.now() - datetime.timedelta(days=2)
        old_question = Question(pub_date=time)
        assert old_question.was_published_recently() is False

    def test_was_published_recently_with_future_question(self):
        time = timezone.now() + datetime.timedelta(days=1)
        future_question = Question(pub_date=time)
        assert future_question.was_published_recently() is False

    def test_index_view_displays_published_question(self, client, published_poll):
        response = client.get(reverse("polls:index"))
        assert response.status_code == 200
        assert published_poll.question_text in response.content.decode()

    def test_index_view_excludes_future_question(self, client, future_poll):
        response = client.get(reverse("polls:index"))
        assert response.status_code == 200
        assert future_poll.question_text not in response.content.decode()

    def test_detail_view_success(self, client, published_poll):
        url = reverse("polls:detail", args=(published_poll.id,))
        response = client.get(url)
        assert response.status_code == 200
        assert published_poll.question_text in response.content.decode()
        assert "Google Cloud Platform" in response.content.decode()

    def test_detail_view_excludes_future_question(self, client, future_poll):
        url = reverse("polls:detail", args=(future_poll.id,))
        response = client.get(url)
        assert response.status_code == 404

    def test_vote_success_increments_count(self, client, published_poll):
        choice = published_poll.choice_set.first()
        initial_votes = choice.votes

        url = reverse("polls:vote", args=(published_poll.id,))
        response = client.post(url, {"choice": choice.id})
        assert response.status_code == 302
        assert response.url == reverse("polls:results", args=(published_poll.id,))

        choice.refresh_from_db()
        assert choice.votes == initial_votes + 1

    def test_vote_without_choice_selection(self, client, published_poll):
        url = reverse("polls:vote", args=(published_poll.id,))
        response = client.post(url, {})  # No choice submitted
        assert response.status_code == 200
        assert "select a choice" in response.content.decode()

    def test_vote_invalid_choice_id(self, client, published_poll):
        url = reverse("polls:vote", args=(published_poll.id,))
        response = client.post(url, {"choice": 99999})
        assert response.status_code == 200
        assert "select a choice" in response.content.decode()


    def test_results_view(self, client, published_poll):
        url = reverse("polls:results", args=(published_poll.id,))
        response = client.get(url)
        assert response.status_code == 200
        assert published_poll.question_text in response.content.decode()
        assert "Google Cloud Platform" in response.content.decode()

    def test_closepoll_command_closes_poll(self, published_poll):
        assert published_poll.opened is True
        call_command("closepoll", published_poll.id)
        published_poll.refresh_from_db()
        assert published_poll.opened is False

    def test_closepoll_command_delete_flag(self, published_poll):
        poll_id = published_poll.id
        call_command("closepoll", poll_id, delete=True)
        assert not Question.objects.filter(id=poll_id).exists()

    def test_closepoll_command_invalid_poll_id(self):
        with pytest.raises(CommandError):
            call_command("closepoll", 99999)

    def test_function_views_direct_call(self, rf, published_poll):
        from polls import views
        request = rf.get("/polls/")
        res_index = views.index(request)
        assert res_index.status_code == 200

        res_detail = views.detail(request, published_poll.id)
        assert res_detail.status_code == 200

        res_results = views.results(request, published_poll.id)
        assert res_results.status_code == 200

