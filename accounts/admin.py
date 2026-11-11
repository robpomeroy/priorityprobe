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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user" and not request.user.is_superuser:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            kwargs["queryset"] = User.objects.filter(id=request.user.id)
            kwargs["initial"] = request.user.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        if not request.user.is_superuser:
            # A user only has at most one UserLLMConfig (OneToOne)
            return not UserLLMConfig.objects.filter(user=request.user).exists()
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.user != request.user:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.user != request.user:
            return False
        return super().has_delete_permission(request, obj)
