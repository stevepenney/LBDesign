from django.shortcuts import redirect
from django.views.generic import TemplateView


class LandingView(TemplateView):
    template_name = 'accounts/landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('projects:project_list')
        return super().dispatch(request, *args, **kwargs)


landing = LandingView.as_view()
