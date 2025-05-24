from django.urls import path
from . import views

urlpatterns = [
    path('workspaces/<int:workspace_id>/simple-compare/', views.simple_compare, name='simple_compare'),
] 