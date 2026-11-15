from django import template

# reusing code https://stackoverflow.com/a/9480134/5288758

register = template.Library()


@register.inclusion_tag('custom_tags/results.html')
def show_results(model):
    """
    Shows the results from a poll question model.

    :param model: Question instance with a choice_set relation
    :return: template context containing choices
    """
    return {'choices': model.choice_set.all()}
