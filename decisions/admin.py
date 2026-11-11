from django.contrib import admin
from decisions.models import DecisionRecord, LLMReflectionLog
from frameworks.models import Framework, Domain, Why, Objective

@admin.register(DecisionRecord)
class DecisionRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "framework", "status", "created_at", "updated_at")
    list_filter = ("status", "framework")
    search_fields = ("title", "proposal_description", "decision_outcome")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(framework__owner=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.framework.owner != request.user:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.framework.owner != request.user:
            return False
        return super().has_delete_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "framework" and not request.user.is_superuser:
            kwargs["queryset"] = Framework.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "affected_domains":
                kwargs["queryset"] = Domain.objects.filter(framework__owner=request.user)
            elif db_field.name == "relevant_whys":
                kwargs["queryset"] = Why.objects.filter(domain__framework__owner=request.user)
            elif db_field.name in ("supporting_objectives", "conflicting_objectives"):
                kwargs["queryset"] = Objective.objects.filter(primary_domain__framework__owner=request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

@admin.register(LLMReflectionLog)
class LLMReflectionLogAdmin(admin.ModelAdmin):
    list_display = ("__str__", "framework", "provider_used", "created_at")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(framework__owner=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.framework.owner != request.user:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.framework.owner != request.user:
            return False
        return super().has_delete_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "framework":
                kwargs["queryset"] = Framework.objects.filter(owner=request.user)
            elif db_field.name == "decision":
                kwargs["queryset"] = DecisionRecord.objects.filter(framework__owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
