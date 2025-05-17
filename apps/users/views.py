from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from django.contrib import messages

from django.views import View
# Create your views here.

class IndexView(View):
    def get(self, request):
        return render(request, 'index.html')

class RegisterView(View):
    def get(self, request):

        if request.user.is_authenticated:
            return redirect('index')
        return render(request, 'register.html')
    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST['email']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']

        new_user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)

        return redirect('login')

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('index')
        return render(request, 'login.html')
    def post(self, request):

        username = request.POST['username']
        password = request.POST['password']
        print(username, password)

        authenticate_user = authenticate(request, username=username, password=password)
        print(authenticate_user)
        if authenticate_user is None:
            messages.error(request, 'Invalid Credentials')
            return render(request, 'login.html')

        login(request, authenticate_user)
        return redirect('index')
