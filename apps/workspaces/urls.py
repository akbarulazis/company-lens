from django.urls import path
from .views import (
    WorkspaceListView, 
    WorkspaceCreateView, 
    WorkspaceUpdateView, 
    WorkspaceDeleteView,
    WorkspaceDetailView
)

from ..companies.views import ResearchCompanyView, CompanyDetailView, DeleteCompanyView

urlpatterns = [
    path('', WorkspaceListView.as_view(), name='workspace_list'),
    path('create/', WorkspaceCreateView.as_view(), name='workspace_create'),
    path('<int:pk>/', WorkspaceDetailView.as_view(), name='workspace_detail'),
    path('<int:pk>/update/', WorkspaceUpdateView.as_view(), name='workspace_update'),
    path('<int:pk>/delete/', WorkspaceDeleteView.as_view(), name='workspace_delete'),
    path('<int:pk>/research/', ResearchCompanyView.as_view(), name='research'),
    path('<int:workspace_id>/research/<str:company_name>', CompanyDetailView.as_view(), name='company_detail'),
    path('<int:workspace_id>/research/<str:company_name>/delete/', DeleteCompanyView.as_view(), name='delete_company')
] 