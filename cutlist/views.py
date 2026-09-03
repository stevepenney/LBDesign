import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import Organisation
from core.models import UsageEvent
from core.usage import log_usage_event
from products.models import Product, TimberTypeDefaultStockLengths
from projects.models import Project
from projects.views import _assert_project_access, _get_projects_for_user
from .models import CutlistProject, MemberProductMapping


def _assert_cutlist_access(user, cutlist):
    if cutlist.project.organisation != user.organisation:
        if not (user.is_lb_admin or user.is_lb_detailing):
            raise PermissionDenied


def _normalize_member_name(name):
    """Whitespace/case-normalized lookup key — mirrors normalizeMemberName() in cutlist.js."""
    return re.sub(r'\s+', '', name or '').upper()


@login_required
def project_list(request):
    projects = _get_projects_for_user(request.user)
    cutlists = CutlistProject.objects.filter(
        project__in=projects
    ).select_related('project', 'created_by')
    return render(request, 'cutlist/project_list.html', {'cutlists': cutlists})


@login_required
def project_new_quick(request):
    """Create a project + blank cutlist in one step and go straight to it."""
    is_lb_staff = request.user.is_lb_admin or request.user.is_lb_detailing

    if is_lb_staff:
        org_pk = request.GET.get('org')
        if not org_pk:
            return redirect(f"{reverse('projects:select_merchant')}?next=cutlist")
        org = get_object_or_404(Organisation, pk=org_pk)
    else:
        if not request.user.organisation:
            messages.error(request, 'Your account is not linked to an organisation. Contact LumberBank.')
            return redirect('projects:project_list')
        org = request.user.organisation

    project = Project.objects.create(
        organisation = org,
        created_by   = request.user,
        status       = Project.Status.PRELIMINARY,
    )
    cutlist = CutlistProject.objects.create(project=project, created_by=request.user)
    return redirect('cutlist:project_edit', pk=cutlist.pk)


@login_required
@require_POST
def project_new(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not _assert_project_access(request.user, project):
        raise PermissionDenied
    cutlist = CutlistProject.objects.create(
        project    = project,
        created_by = request.user,
    )
    return redirect('cutlist:project_edit', pk=cutlist.pk)


@login_required
def project_edit(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)
    products = list(
        Product.objects.filter(is_active=True)
        .select_related('product_type')
        .values('id', 'name', 'product_type__name', 'stock_lengths')
    )
    member_mappings = {
        m.normalized_name: {'product_id': m.product_id, 'product_name': m.product.name}
        for m in MemberProductMapping.objects.select_related('product')
    }
    timber_type_defaults = {
        t.timber_type: t.stock_lengths_list()
        for t in TimberTypeDefaultStockLengths.objects.all()
    }
    return render(request, 'cutlist/project_edit.html', {
        'project': cutlist,
        'products': products,
        'member_mappings': member_mappings,
        'timber_type_defaults': timber_type_defaults,
    })


@login_required
@require_POST
def member_mapping_save(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    raw_name = (data.get('raw_name') or '').strip()
    if not raw_name:
        return JsonResponse({'ok': False, 'error': 'raw_name required'}, status=400)
    normalized_name = _normalize_member_name(raw_name)

    product_id = data.get('product_id')
    if not product_id:
        MemberProductMapping.objects.filter(normalized_name=normalized_name).delete()
        return JsonResponse({'ok': True})

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    MemberProductMapping.objects.update_or_create(
        normalized_name=normalized_name,
        defaults={'raw_name': raw_name[:100], 'product': product},
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def project_save(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    cutlist.state = data
    cutlist.save(update_fields=['state', 'updated_at'])
    log_usage_event(request.user, UsageEvent.EventType.CUTLIST_SAVED)

    return JsonResponse({'ok': True, 'name': cutlist.name})


@login_required
@require_POST
def project_update_field(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)

    if request.POST.get('field') != 'name':
        return JsonResponse({'ok': False, 'error': 'Invalid field'}, status=400)

    value = request.POST.get('value', '').strip()
    cutlist.name = value[:100] or 'Untitled Cutlist'
    cutlist.save(update_fields=['name', 'updated_at'])
    return JsonResponse({'ok': True, 'value': cutlist.name})


@login_required
@require_POST
def project_duplicate(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)

    new_cutlist = CutlistProject.objects.create(
        project    = cutlist.project,
        created_by = request.user,
        name       = f'Copy of {cutlist.name}'[:100],
        state      = cutlist.state,
    )
    return redirect('cutlist:project_edit', pk=new_cutlist.pk)


@login_required
def project_print(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)
    return render(request, 'cutlist/print_view.html', {'project': cutlist})


@login_required
@require_POST
def project_delete(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)
    cutlist.delete()
    return redirect('cutlist:project_list')
