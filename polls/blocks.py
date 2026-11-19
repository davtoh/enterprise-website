from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class PollEmbedBlock(blocks.StructBlock):
    """Composable Wagtail block for embedding a published Poll Question."""

    heading = blocks.CharBlock(label=_("Heading"), required=False, max_length=160)
    question_id = blocks.IntegerBlock(
        label=_("Poll Question ID"),
        min_value=1,
        help_text=_("ID of the published poll Question to embed."),
    )

    class Meta:
        icon = "list-ul"
        label = _("Poll Embed")
        template = "cms/blocks/poll_embed_block.html"

    def get_context(self, value, parent_context=None):
        """Resolve only published, open polls for public CMS rendering."""
        from .models import Question

        context = super().get_context(value, parent_context=parent_context)
        question_id = value.get("question_id")
        question = (
            Question.objects.filter(
                pk=question_id,
                pub_date__lte=timezone.now(),
                opened=True,
            )
            .prefetch_related("choice_set")
            .first()
            if question_id
            else None
        )
        choices = list(question.choice_set.all()) if question else []
        context["question"] = question
        context["choices"] = choices
        context["total_votes"] = sum(choice.votes for choice in choices)
        return context
