from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def help_trigger(slug, label="What's this?"):
    return format_html(
        '<button type="button" class="help-trigger" data-help-slug="{}" aria-label="Help">{}</button>',
        slug,
        label,
    )
