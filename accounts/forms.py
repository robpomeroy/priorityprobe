import ipaddress
import socket
from urllib.parse import urlparse
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from accounts.models import UserLLMConfig

ALLOWED_PROVIDERS = {"ollama", "openrouter", "openai", "anthropic", "gemini", "custom", "none"}

def is_safe_ollama_endpoint(hostname: str) -> bool:
    """
    Checks if an Ollama hostname/IP is permitted.
    Private/internal network ranges or cloud metadata are prohibited unless explicitly allowlisted.
    In hosted production deployments, loopback/private destinations are blocked unless
    specifically configured in settings.OLLAMA_ALLOWED_HOSTS.
    """
    allowlist = getattr(settings, "OLLAMA_ALLOWED_HOSTS", None)
    if allowlist is not None and hostname in allowlist:
        return True

    # In local development (DEBUG=True), allow localhost and 127.0.0.1 by default
    if getattr(settings, "DEBUG", False):
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return True

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback:
            return bool(getattr(settings, "DEBUG", False))
        if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    except ValueError:
        # Resolve hostname to check destination IP
        try:
            resolved_ip_str = socket.gethostbyname(hostname)
            resolved_ip = ipaddress.ip_address(resolved_ip_str)
            if resolved_ip.is_loopback:
                return bool(getattr(settings, "DEBUG", False))
            if resolved_ip.is_private or resolved_ip.is_link_local or resolved_ip.is_reserved:
                return False
        except Exception:
            return False

    return True

def validate_llm_api_base(provider: str, api_base: str):
    if not api_base or provider == "none":
        return api_base
    
    parsed = urlparse(api_base)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError("API Base URL must use http or https scheme.")
    
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValidationError("Invalid API Base hostname.")

    if hostname in ("169.254.169.254", "metadata.google.internal"):
        raise ValidationError("Access to cloud metadata endpoints is prohibited.")

    if provider == "openrouter":
        if hostname not in ("openrouter.ai", "www.openrouter.ai"):
            raise ValidationError("OpenRouter API Base must point to openrouter.ai (e.g. https://openrouter.ai/api/v1).")
        if parsed.scheme != "https":
            raise ValidationError("OpenRouter connections must use HTTPS.")

    elif provider == "openai":
        if hostname not in ("api.openai.com",):
            raise ValidationError("OpenAI API Base must point to api.openai.com (e.g. https://api.openai.com/v1).")
        if parsed.scheme != "https":
            raise ValidationError("OpenAI connections must use HTTPS.")

    elif provider == "anthropic":
        if hostname not in ("api.anthropic.com",):
            raise ValidationError("Anthropic API Base must point to api.anthropic.com (e.g. https://api.anthropic.com/v1).")
        if parsed.scheme != "https":
            raise ValidationError("Anthropic connections must use HTTPS.")

    elif provider == "gemini":
        if hostname not in ("generativelanguage.googleapis.com",):
            raise ValidationError("Google Gemini API Base must point to generativelanguage.googleapis.com.")
        if parsed.scheme != "https":
            raise ValidationError("Gemini connections must use HTTPS.")

    elif provider in ("ollama", "custom"):
        if not is_safe_ollama_endpoint(hostname):
            raise ValidationError(f"Disallowed {provider} destination: private, link-local, or unresolvable internal hostnames are prohibited.")

    return api_base

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Create a password"}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password"}))

    class Meta:
        model = User
        fields = ("username", "email")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email address"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password_confirm", "Passwords do not match.")
            else:
                temp_user = User(
                    username=cleaned_data.get("username", ""),
                    email=cleaned_data.get("email", ""),
                )
                try:
                    validate_password(p1, user=temp_user)
                except ValidationError as error:
                    self.add_error("password", error)
        return cleaned_data

class UserLLMConfigForm(forms.ModelForm):
    raw_api_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"class": "form-control", "placeholder": "Enter new API key (leave blank to keep existing)"}),
        help_text="Key is securely encrypted at rest. Not required for local Ollama.",
    )

    class Meta:
        model = UserLLMConfig
        fields = ("provider", "model_name", "api_base", "consent_given", "theme_preference")
        widgets = {
            "provider": forms.Select(attrs={"class": "form-select"}),
            "model_name": forms.TextInput(attrs={"class": "form-control"}),
            "api_base": forms.TextInput(attrs={"class": "form-control"}),
            "consent_given": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "theme_preference": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        provider = cleaned_data.get("provider")
        api_base = cleaned_data.get("api_base")
        if provider and api_base:
            try:
                validate_llm_api_base(provider, api_base)
            except ValidationError as e:
                self.add_error("api_base", e)
        return cleaned_data
