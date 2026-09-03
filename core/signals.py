from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import UsageEvent
from .usage import log_usage_event


@receiver(user_logged_in)
def log_login_event(sender, request, user, **kwargs):
    log_usage_event(user, UsageEvent.EventType.LOGIN)
