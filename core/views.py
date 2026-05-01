from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Feedback


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
