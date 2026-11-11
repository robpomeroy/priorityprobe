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

@login_required
def test_llm_connection_view(request):
    if request.method != "POST":
        return redirect("accounts:settings")
    config = getattr(request.user, "llm_config", None)
    if not config or config.provider == "none" or not config.model_name:
        messages.warning(request, "Please configure an active LLM provider before testing.")
        return redirect("accounts:settings")
    if not config.consent_given:
        messages.warning(request, "Consent must be granted before connecting to external LLMs.")
        return redirect("accounts:settings")

    from llm.service import generate_reflection
    success, response_text = generate_reflection(
        user_context_markdown="Ping test connection from PrioritySuite settings.",
        user_prompt="Reply with exactly: 'PrioritySuite thinking partner connection verified.'",
        provider=config.provider,
        model_name=config.model_name,
        api_key=config.api_key,
        api_base=config.api_base,
    )
    if success:
        messages.success(request, f"Connection verified successfully! ({config.provider}: {config.model_name})")
    else:
        messages.error(request, f"Connection failed: {response_text}")
    return redirect("accounts:settings")
