from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from ..workspaces.models import Workspace, WorkspaceCompany
from .models import CompanyProfile, Company
from django.contrib import  messages
from .tasks import process_research, compare_profiles, process_document
from .utils import markdown_to_html
# Create your views here.
class ResearchCompanyView(LoginRequiredMixin, View):
    def get(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk, user=request.user)
        # Check if a company name was provided in the URL parameters
        company_name = request.GET.get("company_name")
        context = {"workspace": workspace}
        
        if company_name:
            context["prefilled_company"] = company_name
        
        return render(request, "research_company.html", context)

    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk, user=request.user)
        company_name = request.POST.get("company_name")
        print(company_name)
        if company_name:
            # Check if workspace has reached the limit of 3 companies
            if workspace.get_companies_count() >= 3:
                messages.error(request,
                               "Workspace already has 3 companies. Please remove a company or create a new workspace.")
                return redirect('workspace_detail', pk=workspace.id)

            process_research(workspace.id, company_name)
            messages.success(request, f"Research process started for {company_name}")
            return redirect('workspace_detail', pk=workspace.id)
        return redirect('research_company', pk=workspace.id)


class CompanyDetailView(LoginRequiredMixin, View):
    def get(self, request, workspace_id, company_name):
        workspace= get_object_or_404(Workspace, id=workspace_id)
        try:
            profile = get_object_or_404(CompanyProfile, company_name=company_name, workspace=workspace)
            # documents = CompanyDocument.objects.filter(company=profile).order_by('-uploaded_at')
            print(profile)

            # Convert markdown to HTML
            profile.profile_content = markdown_to_html(profile.profile_content)

            return render(request, "company_detail.html", {
                "workspace": workspace,
                "profile": profile
                # "documents": documents
            })
        except CompanyProfile.DoesNotExist:
            messages.error(request, "Company profile not found")
            return redirect('workspace_detail', workspace_id=workspace.id)


class DeleteCompanyView(LoginRequiredMixin, View):
    def post(self, request, workspace_id, company_name):
        workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)
        profile = get_object_or_404(CompanyProfile, company_name=company_name, workspace=workspace)
        company = get_object_or_404(Company,name=company_name)

        profile.delete()
        company.delete()

        messages.success(request, f"Company '{company_name}' has been removed from workspace")
        return redirect('workspace_detail', pk=workspace_id)