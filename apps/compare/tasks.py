from core.methods import send_notification
from huey.contrib.djhuey import task
from django.utils.html import mark_safe
from apps.companies.models import Company, CompanyProfile
from apps.workspaces.models import Workspace
from .methods import generate_comparison_with_openai
import json
import logging

logger = logging.getLogger(__name__)

@task()
def process_comparison(workspace_id, company_ids):
    """Process company comparison asynchronously using Huey"""
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        
        # Validate company selection
        if not company_ids or len(company_ids) < 2:
            send_notification("notification", "Please select at least 2 companies to compare.")
            return
        
        if len(company_ids) > 4:
            send_notification("notification", "You can compare up to 3 companies at once.")
            return
        
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
                send_notification(
                    "notification", 
                    f"The following companies don't have profiles and can't be compared: {missing_list}."
                )
                return
        
        # Send notification that comparison is starting
        company_names = [profile.company.name for profile in profiles]
        if len(company_names) == 2:
            comparison_text = f"{company_names[0]} vs {company_names[1]}"
        else:
            comparison_text = f"{', '.join(company_names[:-1])} and {company_names[-1]}"
            
        send_notification("notification", f"Starting comparison of {comparison_text}...")
        
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
        
        # Generate comparison using OpenAI
        comparison_html = generate_comparison_with_openai(companies_data)
        
        # Send the result as a notification
        send_notification("comparison_result", comparison_html)
        send_notification("notification", "Comparison completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in process_comparison: {str(e)}")
        send_notification("notification", f"Error generating comparison: {str(e)}")
