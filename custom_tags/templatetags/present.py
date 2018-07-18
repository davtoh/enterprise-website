from django import template, conf
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.template.loader import render_to_string, get_template
import os
from django.template.defaulttags import load

# reusing code https://stackoverflow.com/a/9480134/5288758

register = template.Library()


@register.inclusion_tag('custom_tags/results.html')
def show_results(model):
    """
    Shows the results from a model

    :param model:
    :return:
    """
    return {'choices': model.choice_set.all()}