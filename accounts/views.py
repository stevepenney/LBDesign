from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from .forms import OrganisationForm


class LandingView(TemplateView):
    template_name = 'accounts/landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('projects:project_list')
        return super().dispatch(request, *args, **kwargs)


landing = LandingView.as_view()


def _lb_staff_required(request):
    return request.user.is_authenticated and (
        request.user.is_lb_admin or request.user.is_lb_detailing
    )


@login_required
def organisation_create(request):
    if not _lb_staff_required(request):
        messages.error(request, 'Access denied.')
        return redirect('projects:project_list')

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        form = OrganisationForm(request.POST)
        if form.is_valid():
            org = form.save()
            messages.success(request, f'"{org.name}" created.')
            if next_url:
                return redirect(next_url)
            return redirect('projects:select_merchant')
    else:
        form = OrganisationForm(initial={'is_merchant': True, 'is_active': True})

    return render(request, 'accounts/organisation_form.html', {
        'form': form,
        'next': next_url,
    })
