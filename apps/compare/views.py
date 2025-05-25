from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils.html import mark_safe

from apps.workspaces.models import Workspace, WorkspaceCompany
from apps.companies.models import Company, CompanyProfile
from core.openai_client import openai_with_retry
from apps.compare.methods import generate_comparison_with_openai
from apps.compare.tasks import process_comparison

import json
import logging
import traceback

logger = logging.getLogger(__name__)

@login_required
def async_compare(request, workspace_id):
    """Compare company profiles asynchronously using Redis Huey"""
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)
    
    if request.method == 'POST':
        # Get selected company IDs
        company_ids = request.POST.getlist('company_ids')
        
        if not company_ids or len(company_ids) < 2:
            messages.error(request, "Please select at least 2 companies to compare.")
            return redirect('compare', workspace_id=workspace_id)
        
        if len(company_ids) > 4:
            messages.error(request, "You can compare up to 3 companies at once.")
            return redirect('compare', workspace_id=workspace_id)
        
        # Queue the comparison task using Huey
        process_comparison(workspace_id, company_ids)
        
        # Redirect to waiting page
        messages.success(request, "Comparison process started. Please wait while we generate the comparison.")
        return render(request, 'comparison_processing.html', {
            'workspace': workspace,
            'company_ids': company_ids
        })
    
    # Get companies registered in this workspace
    workspace_companies = WorkspaceCompany.objects.filter(
        workspace=workspace
    ).select_related('company')
    
    # Instead of filtering out companies without profiles,
    # we'll mark them so they can still be shown in the UI
    companies_with_profiles_status = []
    companies_without_profiles = []
    
    for workspace_company in workspace_companies:
        # Check if company has a profile in this workspace
        has_profile = CompanyProfile.objects.filter(
            company=workspace_company.company,
            workspace=workspace
        ).exists()
        
        # Add to list with profile status
        companies_with_profiles_status.append({
            'workspace_company': workspace_company,
            'has_profile': has_profile
        })
        
        # Keep track of companies without profiles for the warning message
        if not has_profile:
            companies_without_profiles.append(workspace_company.company.name)
    
    # Add warning message if some companies don't have profiles
    if companies_without_profiles:
        companies_list = ", ".join(companies_without_profiles)
        messages.warning(
            request, 
            f"The following companies don't have profiles and can't be compared: {companies_list}"
        )
    
    return render(request, 'comparison_select.html', {
        'workspace': workspace,
        'workspace_companies': companies_with_profiles_status
    })
