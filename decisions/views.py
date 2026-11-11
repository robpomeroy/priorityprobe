from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decisions.models import DecisionRecord, DecisionStatus, LLMReflectionLog
from decisions.forms import DecisionRecordForm
from frameworks.models import Framework
from exports.services import generate_decision_markdown
from llm.service import generate_reflection

@login_required
def decision_list_view(request):
    decisions = DecisionRecord.objects.filter(framework__owner=request.user).select_related("framework")
    return render(request, "decisions/decision_list.html", {"decisions": decisions})

@login_required
def decision_create_view(request):
    framework = Framework.objects.filter(owner=request.user).first()
    if not framework:
        framework = Framework.objects.create(owner=request.user, name="My Priorities")
        
    if request.method == "POST":
        form = DecisionRecordForm(request.POST, framework=framework)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.framework = framework
            decision.save()
            form.save_m2m()
            messages.success(request, f"Created decision assessment '{decision.title}'.")
            return redirect("decisions:decision_detail", decision_id=decision.id)
    else:
        form = DecisionRecordForm(framework=framework)
    return render(request, "decisions/decision_form.html", {
        "form": form,
        "framework": framework,
        "title": "New Cross-Domain Decision Assessment",
    })

@login_required
def decision_detail_view(request, decision_id):
    decision = get_object_or_404(
        DecisionRecord.objects.prefetch_related(
            "affected_domains", "relevant_whys__domain", "supporting_objectives__primary_domain",
            "conflicting_objectives__primary_domain", "reflections"
        ),
        id=decision_id,
        framework__owner=request.user
    )
    llm_config = getattr(request.user, "llm_config", None)
    return render(request, "decisions/decision_detail.html", {
        "decision": decision,
        "llm_config": llm_config,
    })

@login_required
def decision_edit_view(request, decision_id):
    decision = get_object_or_404(DecisionRecord, id=decision_id, framework__owner=request.user)
    framework = decision.framework
    if request.method == "POST":
        form = DecisionRecordForm(request.POST, instance=decision, framework=framework)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated decision '{decision.title}'.")
            return redirect("decisions:decision_detail", decision_id=decision.id)
    else:
        form = DecisionRecordForm(instance=decision, framework=framework)
    return render(request, "decisions/decision_form.html", {
        "form": form,
        "framework": framework,
        "title": f"Edit Decision Assessment: {decision.title}",
    })

@login_required
def decision_delete_view(request, decision_id):
    decision = get_object_or_404(DecisionRecord, id=decision_id, framework__owner=request.user)
    if request.method == "POST":
        title = decision.title
        decision.delete()
        messages.info(request, f"Decision assessment '{title}' was deleted.")
        return redirect("decisions:decision_list")
    return render(request, "frameworks/confirm_delete.html", {
        "item_type": "Decision Record",
        "item_name": decision.title,
    })

@login_required
def decision_reflect_view(request, decision_id):
    decision = get_object_or_404(DecisionRecord, id=decision_id, framework__owner=request.user)
    if request.method == "POST":
        llm_config = getattr(request.user, "llm_config", None)
        if not llm_config or not llm_config.consent_given:
            messages.error(request, "Please grant consent in LLM Settings before querying external providers.")
            return redirect("accounts:settings")

        user_prompt = request.POST.get("prompt", "Analyze the cross-domain tensions, trade-offs, and alternatives in this proposed decision.")
        context_md = generate_decision_markdown(decision)

        success, response_text = generate_reflection(
            user_context_markdown=context_md,
            user_prompt=user_prompt,
            provider=llm_config.provider,
            model_name=llm_config.model_name,
            api_key=llm_config.api_key,
            api_base=llm_config.api_base,
        )

        if success:
            LLMReflectionLog.objects.create(
                decision=decision,
                framework=decision.framework,
                user_prompt=user_prompt,
                context_snapshot=context_md,
                llm_response=response_text,
                provider_used=f"{llm_config.provider} ({llm_config.model_name})",
            )
            messages.success(request, "Received reflection from thinking partner.")
        else:
            messages.error(request, response_text)

    return redirect("decisions:decision_detail", decision_id=decision.id)
