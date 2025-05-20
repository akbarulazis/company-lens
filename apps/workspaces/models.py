from django.db import models
from django.contrib.auth.models import User

class Workspace(models.Model):
    name = models.CharField(max_length=255, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class WorkspaceCompany(models.Model):
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE)
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'company')
        
    def __str__(self):
        return f"{self.workspace.name} - {self.company.name}"
