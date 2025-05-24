from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils.html import mark_safe

from apps.workspaces.models import Workspace, WorkspaceCompany
from apps.companies.models import Company, CompanyProfile
from core.openai_client import openai_with_retry
from apps.compare.methods import generate_comparison_with_openai

import json
import logging
import traceback

logger = logging.getLogger(__name__)

@login_required
def simple_compare(request, workspace_id):
    """Simple view to directly compare company profiles without using the task system"""
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)
    
    if request.method == 'POST':
        # Get selected company IDs
        company_ids = request.POST.getlist('company_ids')
        
        if not company_ids or len(company_ids) < 2:
            messages.error(request, "Please select at least 2 companies to compare.")
            return redirect('simple_compare', workspace_id=workspace_id)
        
        if len(company_ids) > 4:
            messages.error(request, "You can compare up to 3 companies at once.")
            return redirect('simple_compare', workspace_id=workspace_id)
            
        # Get company profiles
        profiles = CompanyProfile.objects.filter(
            company__id__in=company_ids,
            workspace=workspace
        ).select_related('company')
        
        # Check if we have all the required profiles
        if profiles.count() < len(company_ids):
            # Find which companies are missing profiles
            selected_companies = Company.objects.filter(id__in=company_ids)
            companies_with_profiles = [p.company.id for p in profiles if p.company]
            
            # Try to find profiles by company name for those missing
            missing_profiles = []
            for company in selected_companies:
                if company.id not in companies_with_profiles:
                    # Try to find profile by company name instead
                    profile_by_name = CompanyProfile.objects.filter(
                        company_name=company.name,
                        workspace=workspace
                    ).first()
                    
                    if profile_by_name:
                        # Link the company to the profile if it's not already linked
                        if not profile_by_name.company:
                            profile_by_name.company = company
                            profile_by_name.save()
                        profiles = profiles | CompanyProfile.objects.filter(id=profile_by_name.id)
                    else:
                        missing_profiles.append(company.name)
            
            # If we still have missing profiles after the name check
            if missing_profiles:
                missing_list = ", ".join(missing_profiles)
                messages.error(
                    request, 
                    f"The following companies don't have profiles and can't be compared: {missing_list}. Please ensure all companies have profiles before comparing."
                )
                return redirect('simple_compare', workspace_id=workspace_id)
        
        # Prepare data for the OpenAI comparison
        companies_data = []
        for profile in profiles:
            data = {
                'name': profile.company.name,
                'ticker': profile.company.ticker or "N/A",
                'profile_content': profile.profile_content,
                'industry': profile.industry or "Unknown",
                'financial_health_score': float(profile.financial_health_score) if profile.financial_health_score else 0,
                'business_risk_score': float(profile.business_risk_score) if profile.business_risk_score else 0,
                'growth_potential_score': float(profile.growth_potential_score) if profile.growth_potential_score else 0,
                'industry_position_score': float(profile.industry_position_score) if profile.industry_position_score else 0,
                'external_trends_score': float(profile.external_trends_score) if profile.external_trends_score else 0,
                'overall_score': float(profile.overall_score) if profile.overall_score else 0,
                'financial_health_insight': profile.financial_health_insight or "No data",
                'business_risk_insight': profile.business_risk_insight or "No data",
                'growth_potential_insight': profile.growth_potential_insight or "No data",
                'industry_position_insight': profile.industry_position_insight or "No data",
                'external_trends_insight': profile.external_trends_insight or "No data",
                'overall_insight': profile.overall_insight or "No data",
            }
            companies_data.append(data)
        
        try:
            # Generate comparison using OpenAI
            comparison_html = generate_comparison_with_openai(companies_data)
            
            # Render the comparison result
            return render(request, 'comparison_result.html', {
                'workspace': workspace,
                'comparison_html': mark_safe(comparison_html),
                'companies': [p.company for p in profiles]
            })
        except Exception as e:
            logger.error(f"Error generating comparison with OpenAI: {str(e)}")
            messages.error(request, f"Error generating comparison: {str(e)}")
            return redirect('simple_compare', workspace_id=workspace_id)
    
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
