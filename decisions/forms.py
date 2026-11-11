from django import forms
from decisions.models import DecisionRecord, DecisionStatus
from frameworks.models import Domain, Why, Objective

class DecisionRecordForm(forms.ModelForm):
    class Meta:
        model = DecisionRecord
        fields = (
            "title",
            "proposal_description",
            "affected_domains",
            "relevant_whys",
            "supporting_objectives",
            "conflicting_objectives",
            "benefits_and_costs",
            "alternatives_considered",
            "unresolved_questions",
            "decision_outcome",
            "status",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Job promotion involving longer hours and travel"}),
            "proposal_description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Describe what is being considered, the circumstances, and what would change..."}),
            "affected_domains": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "relevant_whys": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "supporting_objectives": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "conflicting_objectives": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "benefits_and_costs": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Benefits, direct costs, and opportunity costs..."}),
            "alternatives_considered": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Alternative ways of pursuing the same underlying outcome..."}),
            "unresolved_questions": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "What open questions or missing facts need clarification?"}),
            "decision_outcome": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Decision made, conditions agreed, or final reasoning..."}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, framework=None, **kwargs):
        super().__init__(*args, **kwargs)
        if framework:
            self.fields["affected_domains"].queryset = framework.domains.all()
            self.fields["relevant_whys"].queryset = Why.objects.filter(domain__framework=framework).select_related("domain")
            self.fields["supporting_objectives"].queryset = Objective.objects.filter(primary_domain__framework=framework).select_related("primary_domain")
            self.fields["conflicting_objectives"].queryset = Objective.objects.filter(primary_domain__framework=framework).select_related("primary_domain")
