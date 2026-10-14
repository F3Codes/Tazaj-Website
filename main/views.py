from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Food

def home(request):
    return render(request, "home.html")

def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Tazaj, {user.username}!")
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form})

def browse(request):
    foods = (
        Food.objects
        .filter(is_active=True, shop__is_active=True)
        .select_related('shop')
        .order_by('pickup_end')
    )
    return render(request, 'browse.html', {'foods': foods})