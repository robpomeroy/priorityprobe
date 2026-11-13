import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.forms import UserRegistrationForm, UserLLMConfigForm
from accounts.models import UserLLMConfig

logger = logging.getLogger(__name__)

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
        old_provider = config.provider
        form = UserLLMConfigForm(request.POST, instance=config)
        if form.is_valid():
            cfg = form.save(commit=False)
            new_key = form.cleaned_data.get("raw_api_key")
            if new_key:
                cfg.api_key = new_key
            elif cfg.provider != old_provider:
                # Do not retain previous provider's key when provider changes
                cfg.api_key = ""
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

    # Allow testing unsaved form values if submitted directly from settings form
    if "provider" in request.POST:
        provider = request.POST.get("provider", "none")
        model_name = request.POST.get("model_name", "").strip()
        api_base = request.POST.get("api_base", "").strip()
        consent_given = str(request.POST.get("consent_given", "")).lower() in ("on", "true", "1") or request.POST.get("consent_given") is True
        raw_key = (request.POST.get("raw_api_key") or request.POST.get("api_key") or "").strip()
        # Only reuse saved key if both submitted provider and api_base match saved configuration
        api_base_matches = (api_base == (config.api_base or "").strip()) if config else False
        api_key = raw_key or (config.api_key if (config and config.provider == provider and api_base_matches) else "")
    else:
        if not config:
            messages.warning(request, "Please configure an active LLM provider before testing.")
            return redirect("accounts:settings")
        provider = config.provider
        model_name = config.model_name
        api_base = config.api_base
        consent_given = config.consent_given
        api_key = config.api_key

    valid_providers = {choice[0] for choice in UserLLMConfig.PROVIDER_CHOICES if choice[0] != "none"}
    if provider not in valid_providers or not model_name:
        messages.warning(request, "Please configure an active LLM provider before testing.")
        return redirect("accounts:settings")
    if not consent_given:
        messages.warning(request, "Consent must be granted before connecting to external LLMs.")
        return redirect("accounts:settings")

    from llm.service import generate_reflection
    success, response_text = generate_reflection(
        user_context_markdown="Ping test connection from PrioritySuite settings.",
        user_prompt="Reply with exactly: 'PrioritySuite thinking partner connection verified.'",
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
    )
    if success:
        messages.success(request, f"Connection verified successfully! ({provider}: {model_name})")
    else:
        logger.warning(
            "LLM test connection failure for user '%s' (%s/%s, base=%s): %s",
            request.user.username, provider, model_name, api_base, response_text
        )
        # Preserve specific policy validation errors while sanitizing lower-level stack/connection traces
        if response_text.startswith("Invalid API base URL:") or response_text.startswith("Outbound connection blocked:"):
            display_err = response_text
        elif "Consent" in response_text or "disabled" in response_text or "unconfigured" in response_text:
            display_err = response_text
        else:
            display_err = "The LLM endpoint could not be reached or returned an authentication/connectivity error. Check settings and credentials."
        messages.error(request, f"Connection failed: {display_err}")
    return redirect("accounts:settings")
