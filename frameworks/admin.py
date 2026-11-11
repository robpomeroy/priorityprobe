from django.contrib import admin
from frameworks.models import Framework, Domain, Why, Objective, Goal

@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_sample", "created_at", "updated_at")
    list_filter = ("is_sample", "created_at")
    search_fields = ("name", "owner__username")

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "framework", "display_order", "is_sample")
    list_filter = ("framework", "is_sample")
    search_fields = ("name",)

@admin.register(Why)
class WhyAdmin(admin.ModelAdmin):
    list_display = ("title", "domain", "is_non_negotiable", "is_sample", "last_reviewed_at")
    list_filter = ("is_non_negotiable", "is_sample", "domain__framework")
    search_fields = ("title", "description")

@admin.register(Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    list_display = ("title", "primary_domain", "status", "is_sample", "last_reviewed_at")
    list_filter = ("status", "is_sample", "primary_domain__framework")
    search_fields = ("title", "description")

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "primary_domain", "status", "target_date", "is_sample", "last_reviewed_at")
    list_filter = ("status", "is_sample", "primary_domain__framework")
    search_fields = ("title", "description")
