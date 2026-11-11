from django.contrib import admin
from decisions.models import DecisionRecord, LLMReflectionLog

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

@admin.register(LLMReflectionLog)
class LLMReflectionLogAdmin(admin.ModelAdmin):
    list_display = ("__str__", "framework", "provider_used", "created_at")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(framework__owner=request.user)
