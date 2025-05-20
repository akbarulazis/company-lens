from django.urls import path
from .views import (
    WorkspaceListView, 
    WorkspaceCreateView, 
    WorkspaceUpdateView, 
    WorkspaceDeleteView,
    WorkspaceDetailView
)

urlpatterns = [
    path('', WorkspaceListView.as_view(), name='workspace_list'),
    path('create/', WorkspaceCreateView.as_view(), name='workspace_create'),
    path('<int:pk>/', WorkspaceDetailView.as_view(), name='workspace_detail'),
    path('<int:pk>/update/', WorkspaceUpdateView.as_view(), name='workspace_update'),
    path('<int:pk>/delete/', WorkspaceDeleteView.as_view(), name='workspace_delete'),
] 