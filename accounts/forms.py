from django import forms
from django.contrib.auth.models import User
from accounts.models import UserLLMConfig

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
        widget=forms.PasswordInput(render_value=True, attrs={"class": "form-control", "placeholder": "Enter new API key (leave blank to keep existing)"}),
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
