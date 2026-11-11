from django.contrib import admin
from accounts.models import UserLLMConfig

@admin.register(UserLLMConfig)
class UserLLMConfigAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "model_name", "consent_given", "theme_preference", "updated_at")
    list_filter = ("provider", "consent_given", "theme_preference")
    search_fields = ("user__username", "user__email", "model_name")
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.user != request.user:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.user != request.user:
            return False
        return super().has_delete_permission(request, obj)
