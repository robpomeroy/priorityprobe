import ipaddress
from urllib.parse import urlparse
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from accounts.models import UserLLMConfig

ALLOWED_PROVIDERS = {"ollama", "openrouter", "none"}

def validate_llm_api_base(provider: str, api_base: str):
    if not api_base or provider == "none":
        return api_base
    
    parsed = urlparse(api_base)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError("API Base URL must use http or https scheme.")
    
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValidationError("Invalid API Base hostname.")

    # Check for dangerous metadata IP addresses
    if hostname == "169.254.169.254" or hostname == "metadata.google.internal":
        raise ValidationError("Access to cloud metadata endpoints is prohibited.")

    if provider == "openrouter":
        if hostname not in ("openrouter.ai", "www.openrouter.ai"):
            raise ValidationError("OpenRouter API Base must point to openrouter.ai (e.g. https://openrouter.ai/api/v1).")
        if parsed.scheme != "https":
            raise ValidationError("OpenRouter connections must use HTTPS.")
    
    elif provider == "ollama":
        # Ollama typically runs on localhost or a private LAN host
        pass

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
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Passwords do not match.")
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
