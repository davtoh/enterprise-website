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

# https://gist.github.com/HenrikJoreteg/742160
# https://djangosnippets.org/snippets/10574/
# https://docs.djangoproject.com/en/2.0/howto/custom-template-tags/
# verbatim include https://gist.github.com/gridcell/9476974


register = template.Library()


@register.simple_tag
def raw_include(path):
    """
    Includes a file as-is from the static files.

    WARNING: this is dangerous and this means that the source is trusty

    :param path:
    :return:
    """
    if settings.DEBUG:
        absolute_path = finders.find(path)
        with open(absolute_path) as fd:
            content = fd.read()
    else:
        content = staticfiles_storage.open(path).read()
    return mark_safe(content)  # dangerous, we trust the source file


@register.simple_tag
def verbatim_include(path):
    """
    Includes and scape a file from the static files

    :param path:
    :return:
    """
    if settings.DEBUG:
        absolute_path = finders.find(path)
        with open(absolute_path) as fd:
            content = fd.read()
    else:
        content = staticfiles_storage.open(path).read()
    return escape(content)


@register.simple_tag
def template_include(path):
    """
    Includes a file as-is from the templates. No tags are rendered

    :param path:
    :return:
    """
    return mark_safe(get_template(path).template.source)