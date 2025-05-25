from django.urls import path
from . import views

urlpatterns = [
    path('workspaces/<int:workspace_id>/async-compare/', views.async_compare, name='compare'),
] 