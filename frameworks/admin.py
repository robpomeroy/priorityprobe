from django.contrib import admin
from frameworks.models import Framework, Domain, Why, Objective, Goal

class UserOwnedAdmin(admin.ModelAdmin):
    """
    Limits admin access to the staff user's own framework data,
    respecting tenant isolation while allowing superuser global maintenance.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(self.model, "owner"):
            return qs.filter(owner=request.user)
        if hasattr(self.model, "framework"):
            return qs.filter(framework__owner=request.user)
        if hasattr(self.model, "domain"):
            return qs.filter(domain__framework__owner=request.user)
        if hasattr(self.model, "primary_domain"):
            return qs.filter(primary_domain__framework__owner=request.user)
        return qs

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser:
            owner = getattr(obj, "owner", None)
            if owner is None and hasattr(obj, "framework"):
                owner = obj.framework.owner
            if owner is None and hasattr(obj, "domain"):
                owner = obj.domain.framework.owner
            if owner is None and hasattr(obj, "primary_domain"):
                owner = obj.primary_domain.framework.owner
            if owner != request.user:
                return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser:
            owner = getattr(obj, "owner", None)
            if owner is None and hasattr(obj, "framework"):
                owner = obj.framework.owner
            if owner is None and hasattr(obj, "domain"):
                owner = obj.domain.framework.owner
            if owner is None and hasattr(obj, "primary_domain"):
                owner = obj.primary_domain.framework.owner
            if owner != request.user:
                return False
        return super().has_delete_permission(request, obj)

@admin.register(Framework)
class FrameworkAdmin(UserOwnedAdmin):
    list_display = ("name", "owner", "is_sample", "created_at", "updated_at")
    list_filter = ("is_sample", "created_at")
    search_fields = ("name", "owner__username")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "owner" and not request.user.is_superuser:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            kwargs["queryset"] = User.objects.filter(id=request.user.id)
            kwargs["initial"] = request.user.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(Domain)
class DomainAdmin(UserOwnedAdmin):
    list_display = ("name", "framework", "display_order", "is_sample")
    list_filter = ("framework", "is_sample")
    search_fields = ("name",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "framework" and not request.user.is_superuser:
            kwargs["queryset"] = Framework.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Why)
class WhyAdmin(UserOwnedAdmin):
    list_display = ("title", "domain", "is_non_negotiable", "is_sample", "last_reviewed_at")
    list_filter = ("is_non_negotiable", "is_sample", "domain__framework")
    search_fields = ("title", "description")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "domain" and not request.user.is_superuser:
            kwargs["queryset"] = Domain.objects.filter(framework__owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Objective)
class ObjectiveAdmin(UserOwnedAdmin):
    list_display = ("title", "primary_domain", "status", "is_sample", "last_reviewed_at")
    list_filter = ("status", "is_sample", "primary_domain__framework")
    search_fields = ("title", "description")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "primary_domain" and not request.user.is_superuser:
            kwargs["queryset"] = Domain.objects.filter(framework__owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "whys":
                kwargs["queryset"] = Why.objects.filter(domain__framework__owner=request.user)
            elif db_field.name == "related_domains":
                kwargs["queryset"] = Domain.objects.filter(framework__owner=request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

@admin.register(Goal)
class GoalAdmin(UserOwnedAdmin):
    list_display = ("title", "primary_domain", "status", "target_date", "is_sample", "last_reviewed_at")
    list_filter = ("status", "is_sample", "primary_domain__framework")
    search_fields = ("title", "description")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "primary_domain" and not request.user.is_superuser:
            kwargs["queryset"] = Domain.objects.filter(framework__owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "objectives":
                kwargs["queryset"] = Objective.objects.filter(primary_domain__framework__owner=request.user)
            elif db_field.name == "related_domains":
                kwargs["queryset"] = Domain.objects.filter(framework__owner=request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)
