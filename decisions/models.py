from django.db import models
from django.contrib.auth.models import User
from frameworks.models import Framework, Domain, Why, Objective, Goal

class DecisionStatus(models.TextChoices):
    EXPLORING = "EXPLORING", "Exploring"
    DECIDED = "DECIDED", "Decided"
    ARCHIVED = "ARCHIVED", "Archived"

class DecisionRecord(models.Model):
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="decisions")
    title = models.CharField(max_length=255, help_text="Short title of the opportunity, commitment, or decision")
    proposal_description = models.TextField(help_text="What is proposed or being considered? (e.g. A job promotion with longer hours)")
    
    affected_domains = models.ManyToManyField(Domain, blank=True, related_name="affected_decisions")
    relevant_whys = models.ManyToManyField(Why, blank=True, related_name="relevant_decisions")
    supporting_objectives = models.ManyToManyField(Objective, blank=True, related_name="supporting_decisions")
    conflicting_objectives = models.ManyToManyField(Objective, blank=True, related_name="conflicting_decisions")
    
    benefits_and_costs = models.TextField(blank=True, default="", help_text="Key benefits, direct costs, and opportunity costs")
    alternatives_considered = models.TextField(blank=True, default="", help_text="Alternative courses of action or variations")
    unresolved_questions = models.TextField(blank=True, default="", help_text="Open questions or further information needed before deciding")
    decision_outcome = models.TextField(blank=True, default="", help_text="The decision made and the reasoning behind it")
    
    status = models.CharField(max_length=20, choices=DecisionStatus.choices, default=DecisionStatus.EXPLORING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

class LLMReflectionLog(models.Model):
    decision = models.ForeignKey(DecisionRecord, null=True, blank=True, on_delete=models.CASCADE, related_name="reflections")
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="reflections")
    user_prompt = models.TextField()
    context_snapshot = models.TextField(help_text="Markdown snapshot of framework items shared with LLM")
    llm_response = models.TextField(help_text="Structured reflection received from thinking partner")
    provider_used = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reflection on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
