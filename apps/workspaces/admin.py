from django.contrib import admin
from .models import Workspace, WorkspaceCompany

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at', 'updated_at')
    search_fields = ('name', 'user__username')
    list_filter = ('created_at',)

@admin.register(WorkspaceCompany)
class WorkspaceCompanyAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'company', 'created_at')
    search_fields = ('workspace__name', 'company__name')
    list_filter = ('created_at',)
