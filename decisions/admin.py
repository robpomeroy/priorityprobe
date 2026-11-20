from django.contrib import admin

from decisions.models import DecisionRecord, LLMReflectionLog
from frameworks.admin import UserOwnedAdmin
from frameworks.models import Domain, Framework, Objective, Why


@admin.register(DecisionRecord)
class DecisionRecordAdmin(UserOwnedAdmin):
    list_display = ("title", "framework", "status", "created_at", "updated_at")
    list_filter = ("status", "framework")
    search_fields = ("title", "proposal_description", "decision_outcome")

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
                kwargs["queryset"] = Objective.objects.filter(
                    primary_domain__framework__owner=request.user
                )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(LLMReflectionLog)
class LLMReflectionLogAdmin(UserOwnedAdmin):
    list_display = ("__str__", "framework", "provider_used", "created_at")
    readonly_fields = ("created_at",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "framework":
                kwargs["queryset"] = Framework.objects.filter(owner=request.user)
            elif db_field.name == "decision":
                kwargs["queryset"] = DecisionRecord.objects.filter(framework__owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
