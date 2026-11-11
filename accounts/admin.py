from django.contrib import admin
from accounts.models import UserLLMConfig

@admin.register(UserLLMConfig)
class UserLLMConfigAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "model_name", "consent_given", "theme_preference", "updated_at")
    list_filter = ("provider", "consent_given", "theme_preference")
    search_fields = ("user__username", "user__email", "model_name")
    readonly_fields = ("created_at", "updated_at")
