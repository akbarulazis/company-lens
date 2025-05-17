from django.urls import path
from django.urls import path
from .views import IndexView, RegisterView, LoginView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),


]