from django import template
from polls.templatetags.poll_tags import show_results as _poll_show_results

# reusing code https://stackoverflow.com/a/9480134/5288758

register = template.Library()


@register.inclusion_tag('custom_tags/results.html')
def show_results(model):
    """Backwards-compatible delegate to polls.templatetags.poll_tags.show_results."""
    return _poll_show_results(model)