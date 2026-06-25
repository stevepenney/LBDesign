from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .models import Feedback, HelpTopic


@login_required
@require_POST
def submit_feedback(request):
    comments = request.POST.get('comments', '').strip()
    if not comments:
        return JsonResponse({'ok': False, 'error': 'Please enter some comments.'}, status=400)

    Feedback.objects.create(
        user=request.user,
        page_url=request.POST.get('page_url', '')[:500],
        page_title=request.POST.get('page_title', '')[:255],
        comments=comments,
        screenshot=request.FILES.get('screenshot'),
    )
    return JsonResponse({'ok': True})


@login_required
def help_topic(request, slug):
    try:
        topic = HelpTopic.objects.get(slug=slug)
        return JsonResponse({
            'title': topic.title,
            'body': topic.body,
            'image_url': topic.image.url if topic.image else None,
        })
    except HelpTopic.DoesNotExist:
        return JsonResponse({
            'title': 'Help',
            'body': '<p>No help content has been added for this topic yet.</p>',
            'image_url': None,
        })
