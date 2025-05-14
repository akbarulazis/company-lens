from django.urls import path
from .views import example_view

urlpatterns = [
    path('', example_view, name='example_view'),
]
