from django import template, conf
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.safestring import mark_safe
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.template.loader import render_to_string, get_template
from django.template.defaulttags import load

# https://gist.github.com/HenrikJoreteg/742160
# https://djangosnippets.org/snippets/10574/
# https://docs.djangoproject.com/en/2.0/howto/custom-template-tags/


register = template.Library()


@register.simple_tag
def raw_include(path):
    """from static path"""
    if settings.DEBUG:
        absolute_path = finders.find(path)
        with open(absolute_path) as fd:
            content = fd.read()
    else:
        content = staticfiles_storage.open(path).read()
    return mark_safe(content)


@register.simple_tag
def template_include(path):
    return mark_safe(get_template(path).template.source)