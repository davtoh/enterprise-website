import datetime

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
#timezone.activate('America/Bogota')  # Current time zone


class Question(models.Model):
    question_text = models.CharField(_('Question text'), max_length=200)
    pub_date = models.DateTimeField(_('Date published'), default=timezone.now)
    opened = models.BooleanField(_('Poll status'), default=True)

    class Meta:
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')

    def __str__(self):
        return self.question_text

    def was_published_recently(self):
        now = timezone.now()
        return now - datetime.timedelta(days=1) <= self.pub_date <= now
    # for admin
    was_published_recently.admin_order_field = 'pub_date'
    was_published_recently.boolean = True
    was_published_recently.short_description = _('Published recently?')


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name=_('Question'))
    choice_text = models.CharField(_('Choice text'), max_length=200)
    votes = models.IntegerField(_('Votes'), default=0)

    class Meta:
        verbose_name = _('Choice')
        verbose_name_plural = _('Choices')

    def __str__(self):
        return self.choice_text