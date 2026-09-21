from django import template

register = template.Library()


@register.filter
def user_label(user, fallback='—'):
    """Display name for a nullable user FK (created_by/uploaded_by are SET_NULL on delete).

    Written as a filter because `{{ x.user.get_full_name|default:x.user.username }}` raises
    VariableDoesNotExist when the user is None — filter arguments don't resolve silently.
    """
    if not user:
        return fallback
    return user.get_full_name() or user.get_username()
