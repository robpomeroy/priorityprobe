from django import forms
from frameworks.models import Framework, Domain, Why, Objective, Goal

class FrameworkForm(forms.ModelForm):
    class Meta:
        model = Framework
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Personal Priorities Framework"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional description or context..."}),
        }

class DomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ("name", "description", "display_order")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Family & Home, Work & Vocation"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "What broad area of life are you considering?"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control"}),
        }

class WhyForm(forms.ModelForm):
    class Meta:
        model = Why
        fields = ("title", "description", "is_non_negotiable", "display_order")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Why does this area matter to you? Why should anything happen here?"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Further background, conviction, or commitment details..."}),
            "is_non_negotiable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control"}),
        }

class ObjectiveForm(forms.ModelForm):
    class Meta:
        model = Objective
        fields = ("primary_domain", "title", "description", "whys", "related_domains", "status")
        widgets = {
            "primary_domain": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "What would you like your Whys to lead to?"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "whys": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "related_domains": forms.SelectMultiple(attrs={"class": "form-select", "size": "3"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, framework=None, **kwargs):
        super().__init__(*args, **kwargs)
        if framework:
            self.fields["primary_domain"].queryset = framework.domains.all()
            self.fields["whys"].queryset = Why.objects.filter(domain__framework=framework)
            self.fields["related_domains"].queryset = framework.domains.all()

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ("primary_domain", "title", "description", "objectives", "related_domains", "target_date", "status")
        widgets = {
            "primary_domain": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "What specifically will you do or achieve?"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "objectives": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "related_domains": forms.SelectMultiple(attrs={"class": "form-select", "size": "3"}),
            "target_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, framework=None, **kwargs):
        super().__init__(*args, **kwargs)
        if framework:
            self.fields["primary_domain"].queryset = framework.domains.all()
            self.fields["objectives"].queryset = Objective.objects.filter(primary_domain__framework=framework)
            self.fields["related_domains"].queryset = framework.domains.all()
