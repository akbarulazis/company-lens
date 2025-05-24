from core.methods import send_notification
from huey.contrib.djhuey import task
from .methods import generate_business_profile, generate_query, research, compare_company_finances, \
    analyze_document, calculate_investment_scores
import markdown2
from .models import CompanyProfile, CompanyDocument, Workspace, Company
from ..workspaces.models import WorkspaceCompany
import PyPDF2
import os
import json
import logging

logger = logging.getLogger(__name__)


@task()
def process_research(workspace_id, company_name):
    try:
        workspace = Workspace.objects.get(id=workspace_id)

        # Check if workspace has reached the limit of 3 companies
        if workspace.get_companies_count() >= 3:
            send_notification("notification",
                              "Workspace already has 3 companies. Please remove a company or create a new workspace.")
            return

        send_notification("notification", "Starting company research...")

        # Perform enhanced research
        research_results = research(company_name)
        if not research_results:
            send_notification("notification", "No research results found.")
            return

        # Parse research results
        try:
            results_dict = json.loads(research_results)
            main_info = results_dict.get('Main Company Information', {})
            valid_urls = results_dict.get('Valid URLs Found', [])
            business_results = results_dict.get('Business Analysis Results', [])
        except json.JSONDecodeError:
            # If results are not in JSON format, use as is
            main_info = {'name': company_name}
            valid_urls = []
            business_results = []

        # Generate business profile
        send_notification("notification", "Generating business profile...")
        business_profile = generate_business_profile(research_results, company_name)

        # Save the profile to the database
        profile = CompanyProfile(
            workspace=workspace,
            company_name=company_name,
            industry=main_info.get('industry'),
            profile_content=business_profile
        )

        com_name = Company.objects.create(name=company_name)
        WorkspaceCompany.objects.create(workspace=workspace, company=com_name)

        # Link the company to the profile
        profile.company = com_name
        profile.save()

        # Calculate investment scores
        calculate_company_scores(profile.id)

        # Convert markdown to HTML and send notification
        html = markdown2.markdown(business_profile)
        send_notification("business_profile", html)

    except Exception as e:
        logger.error(f"Error in process_research: {str(e)}")
        send_notification("notification", f"Error during research: {str(e)}")


@task()
def calculate_company_scores(profile_id):
    """Calculate investment scores for a company profile"""
    try:
        profile = CompanyProfile.objects.get(id=profile_id)

        send_notification("notification", f"Calculating investment scores for {profile.company_name}...")

        scores = calculate_investment_scores(profile.profile_content)

        # Update the profile with scores and insights
        profile.financial_health_score = scores.get('financial_health_score', 0)
        profile.business_risk_score = scores.get('business_risk_score', 0)
        profile.growth_potential_score = scores.get('growth_potential_score', 0)
        profile.industry_position_score = scores.get('industry_position_score', 0)
        profile.external_trends_score = scores.get('external_trends_score', 0)

        profile.financial_health_insight = scores.get('financial_health_insight', '')
        profile.business_risk_insight = scores.get('business_risk_insight', '')
        profile.growth_potential_insight = scores.get('growth_potential_insight', '')
        profile.industry_position_insight = scores.get('industry_position_insight', '')
        profile.external_trends_insight = scores.get('external_trends_insight', '')
        profile.overall_insight = scores.get('overall_insight', '')

        # Calculate overall score
        profile.calculate_overall_score()
        profile.save()

        send_notification("notification", f"Investment scoring completed for {profile.company_name}")

    except CompanyProfile.DoesNotExist:
        send_notification("notification", "The requested profile could not be found.")


@task()
def compare_profiles(profile_ids):
    """Compare up to three company profiles and provide insights"""
    try:
        profiles = []
        for profile_id in profile_ids:
            if profile_id:
                try:
                    profile = CompanyProfile.objects.get(id=profile_id)
                    profiles.append(profile)
                except CompanyProfile.DoesNotExist:
                    # Try to find by company ID if direct profile ID fails
                    try:
                        company = Company.objects.get(id=profile_id)
                        profile = CompanyProfile.objects.filter(company=company).first()
                        if profile:
                            profiles.append(profile)
                        else:
                            send_notification("notification", f"No profile found for company: {company.name}")
                    except Company.DoesNotExist:
                        send_notification("notification", f"Could not find profile or company with ID: {profile_id}")
                        continue

        if len(profiles) < 2:
            send_notification("notification", "Please select at least two companies to compare.")
            return

        company_names = [profile.company_name for profile in profiles]
        send_notification("notification", f"Comparing {', '.join(company_names)}...")

        # Get comparison for the profiles
        result = compare_company_finances([profile.profile_content for profile in profiles],
                                          [profile.company_name for profile in profiles])

        html = markdown2.markdown(result)
        send_notification("finance_comparison", html)

    except Exception as e:
        logger.error(f"Error in compare_profiles: {str(e)}")
        send_notification("notification", f"Error comparing profiles: {str(e)}")


@task()
def process_document(document_id):
    """Process uploaded document, extract text and key points"""
    try:
        document = CompanyDocument.objects.get(id=document_id)
        file_path = document.file.path

        send_notification("notification", f"Processing document: {document.title}...")

        # Extract text from PDF
        extracted_text = ""
        if file_path.lower().endswith('.pdf'):
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    extracted_text += page.extract_text()

        document.extracted_text = extracted_text
        document.save()

        # Analyze document for key points
        if extracted_text:
            send_notification("notification", "Extracting key points...")
            key_points = analyze_document(extracted_text, document.company.company_name)
            document.key_points = key_points
            document.save()

            # Recalculate scores with new information
            calculate_company_scores(document.company.id)

        send_notification("notification", f"Document processing completed: {document.title}")

    except CompanyDocument.DoesNotExist:
        send_notification("notification", "The requested document could not be found.")
    except Exception as e:
        send_notification("notification", f"Error processing document: {str(e)}")

