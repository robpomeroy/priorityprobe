from django.db import models
from django.contrib.auth.models import User
from accounts.crypto import encrypt_value, decrypt_value

class UserLLMConfig(models.Model):
    PROVIDER_CHOICES = [
        ("ollama", "Ollama (Local / Self-hosted)"),
        ("openrouter", "OpenRouter (Cloud Router)"),
        ("none", "None / Offline"),
    ]

    THEME_CHOICES = [
        ("auto", "System Default"),
        ("light", "Autumn Parchment (Light)"),
        ("dark", "Autumn Woodland (Dark)"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="llm_config")
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default="ollama")
    _encrypted_api_key = models.TextField(db_column="encrypted_api_key", blank=True, default="")
    model_name = models.CharField(max_length=120, default="ollama/llama3.1", help_text="e.g. ollama/llama3.1 or openrouter/anthropic/claude-3.5-sonnet")
    api_base = models.CharField(max_length=255, blank=True, default="http://localhost:11434", help_text="Base URL (e.g. http://localhost:11434 for Ollama or https://openrouter.ai/api/v1)")
    consent_given = models.BooleanField(default=False, help_text="User consent to share selected framework prompts with external LLM")
    theme_preference = models.CharField(max_length=20, choices=THEME_CHOICES, default="auto")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def api_key(self) -> str:
        return decrypt_value(self._encrypted_api_key)

    @api_key.setter
    def api_key(self, raw_key: str):
        self._encrypted_api_key = encrypt_value(raw_key.strip()) if raw_key else ""

    def __str__(self):
        return f"LLM Config for {self.user.username} ({self.provider}: {self.model_name})"
