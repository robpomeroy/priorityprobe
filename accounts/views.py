from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.forms import UserRegistrationForm, UserLLMConfigForm
from accounts.models import UserLLMConfig

def register_view(request):
    if request.user.is_authenticated:
        return redirect("frameworks:workspace")
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            UserLLMConfig.objects.create(user=user)
            login(request, user)
            messages.success(request, f"Welcome to PrioritySuite, {user.username}!")
            return redirect("frameworks:workspace")
    else:
        form = UserRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})

@login_required
def settings_view(request):
    config, _ = UserLLMConfig.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = UserLLMConfigForm(request.POST, instance=config)
        if form.is_valid():
            cfg = form.save(commit=False)
            new_key = form.cleaned_data.get("raw_api_key")
            if new_key:
                cfg.api_key = new_key
            cfg.save()
            messages.success(request, "Settings updated successfully.")
            return redirect("accounts:settings")
    else:
        form = UserLLMConfigForm(instance=config)
    return render(request, "accounts/settings.html", {"form": form, "config": config})

@login_required
def delete_account_view(request):
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        messages.info(request, "Your account and all associated frameworks and decisions have been completely deleted from PrioritySuite.")
        return redirect("accounts:login")
    return render(request, "accounts/delete_account.html")
