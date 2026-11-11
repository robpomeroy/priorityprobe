from django.db import models
from django.contrib.auth.models import User

class StatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    PAUSED = "PAUSED", "Paused"
    ABANDONED = "ABANDONED", "Abandoned"

class Framework(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="frameworks")
    name = models.CharField(max_length=200, default="My Priorities Framework")
    description = models.TextField(blank=True, default="")
    is_sample = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

class Domain(models.Model):
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="domains")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="", help_text="What broad area of life are you considering?")
    display_order = models.PositiveIntegerField(default=0)
    is_sample = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.name

class Why(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="whys")
    title = models.CharField(max_length=255, help_text="Why does this area matter to you? Why should anything happen here?")
    description = models.TextField(blank=True, default="")
    is_non_negotiable = models.BooleanField(default=False, help_text="Mark if this is an absolute, non-negotiable personal priority")
    display_order = models.PositiveIntegerField(default=0)
    is_sample = models.BooleanField(default=False)
    last_reviewed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.title

class Objective(models.Model):
    primary_domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="primary_objectives")
    whys = models.ManyToManyField(Why, blank=True, related_name="objectives")
    related_domains = models.ManyToManyField(Domain, blank=True, related_name="related_objectives")
    title = models.CharField(max_length=255, help_text="What would you like your Whys to lead to?")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    is_sample = models.BooleanField(default=False)
    last_reviewed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class Goal(models.Model):
    primary_domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="primary_goals")
    objectives = models.ManyToManyField(Objective, blank=True, related_name="goals")
    related_domains = models.ManyToManyField(Domain, blank=True, related_name="related_goals")
    title = models.CharField(max_length=255, help_text="What specifically will you do or achieve?")
    description = models.TextField(blank=True, default="")
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    is_sample = models.BooleanField(default=False)
    last_reviewed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
