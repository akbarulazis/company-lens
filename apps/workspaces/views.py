from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Workspace, WorkspaceCompany
from apps.companies.models import Company

# Create your views here.

class WorkspaceListView(LoginRequiredMixin, View):
    def get(self, request):
        workspaces = Workspace.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'workspace_list.html', {'workspaces': workspaces})

class WorkspaceCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'workspace_form.html')
    
    def post(self, request):
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Workspace name is required')
            return render(request, 'workspace_form.html')
        
        workspace = Workspace.objects.create(
            name=name,
            description=description,
            user=request.user
        )
        
        messages.success(request, f'Workspace "{name}" created successfully')
        return redirect('workspace_detail', pk=workspace.id)

class WorkspaceUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk, user=request.user)
        return render(request, 'workspace_form.html', {'workspace': workspace})
    
    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk, user=request.user)
        
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Workspace name is required')
            return render(request, 'workspace_form.html', {'workspace': workspace})
        
        workspace.name = name
        workspace.description = description
        workspace.save()
        
        messages.success(request, f'Workspace "{name}" updated successfully')
        return redirect('workspace_detail', pk=workspace.id)

class WorkspaceDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk, user=request.user)
        return render(request, 'workspace_confirm_delete.html', {'workspace': workspace})
    
    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk, user=request.user)
        name = workspace.name
        workspace.delete()
        
        messages.success(request, f'Workspace "{name}" deleted successfully')
        return redirect('workspace_list')

class WorkspaceDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk, user=request.user)
        try:
            workspace_companies = WorkspaceCompany.objects.filter(workspace=workspace)
        except Exception:
            # Handle case where there might be issues with the WorkspaceCompany model
            workspace_companies = []
        
        return render(request, 'workspace_detail.html', {
            'workspace': workspace,
            'workspace_companies': workspace_companies
        })
