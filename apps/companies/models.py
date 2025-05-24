from django.db import models
from core.utils import generate_id

from ..workspaces.models import  Workspace, WorkspaceCompany
# Create your models here.

class Company(models.Model):
    name = models.CharField(max_length=255)
    ticker = models.CharField(max_length=10, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Companies"


class CompanyProfile(models.Model):
    """Detailed company analysis specific to a workspace"""
    id = models.CharField(max_length=24, primary_key=True, default=generate_id)
    # Connection to the base Company
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='profiles', null=True, blank=True)
    # Keeping the exact same workspace foreign key relationship
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='companies')
    # We keep company_name for backward compatibility and convenience
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255, blank=True, null=True)
    profile_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Company Enrichment Data
    founded_year = models.IntegerField(null=True, blank=True)
    headquarters = models.CharField(max_length=255, null=True, blank=True)
    employee_count = models.CharField(max_length=50, null=True, blank=True)
    company_website = models.URLField(null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    crunchbase_url = models.URLField(null=True, blank=True)

    # Financial Data
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    annual_revenue = models.CharField(max_length=100, null=True, blank=True)
    funding_total = models.CharField(max_length=100, null=True, blank=True)
    stock_symbol = models.CharField(max_length=20, null=True, blank=True)

    # Investment Scoring (1-5)
    financial_health_score = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    business_risk_score = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    growth_potential_score = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    industry_position_score = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    external_trends_score = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    overall_score = models.DecimalField(max_digits=2, decimal_places=1, default=0)

    # Insights from AI
    financial_health_insight = models.TextField(blank=True, null=True)
    business_risk_insight = models.TextField(blank=True, null=True)
    growth_potential_insight = models.TextField(blank=True, null=True)
    industry_position_insight = models.TextField(blank=True, null=True)
    external_trends_insight = models.TextField(blank=True, null=True)
    overall_insight = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.company_name

    def calculate_overall_score(self):
        scores = [
            self.financial_health_score,
            self.business_risk_score,
            self.growth_potential_score,
            self.industry_position_score,
            self.external_trends_score
        ]
        if all(scores):
            self.overall_score = sum(scores) / len(scores)
            self.save(update_fields=['overall_score'])
        return self.overall_score

    def save(self, *args, **kwargs):
        # If company is not set but company_name is, try to link to an existing company
        if not self.company and self.company_name:
            # Try to find an existing company with the same name
            try:
                company = Company.objects.get(name=self.company_name)
                self.company = company
            except Company.DoesNotExist:
                # Create a new company if none exists
                company = Company.objects.create(name=self.company_name)
                self.company = company
        
        # Call the original save method
        super().save(*args, **kwargs)


class CompanyDocument(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_id)
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50)  # annual_report, financial_statement, etc.
    file = models.FileField(upload_to='company_documents/')
    extracted_text = models.TextField(blank=True, null=True)
    key_points = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company.company_name} - {self.title}"