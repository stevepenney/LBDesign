from .models import UsageEvent


def log_usage_event(user, event_type):
    """
    Record one UsageEvent for a real, user-initiated action. Callers only pass
    a user for request-driven call sites — bulk/system paths (e.g. dummy data
    seeding) simply don't pass one, so nothing gets logged for them.
    """
    if not user or not user.is_authenticated:
        return
    UsageEvent.objects.create(
        user=user,
        organisation=getattr(user, 'organisation', None),
        event_type=event_type,
    )
