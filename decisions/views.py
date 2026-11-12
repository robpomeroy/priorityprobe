from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decisions.models import DecisionRecord, DecisionStatus, LLMReflectionLog
from decisions.forms import DecisionRecordForm
from frameworks.models import Framework, Objective, Goal
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

        raw_prompt = request.POST.get("prompt", "")
        user_prompt = raw_prompt.strip() if raw_prompt and raw_prompt.strip() else "Analyze the cross-domain tensions, trade-offs, and alternatives in this proposed decision."
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

@login_required
def decision_compare_view(request, framework_id=None):
    if framework_id:
        framework = get_object_or_404(Framework, id=framework_id, owner=request.user)
    else:
        framework = Framework.objects.filter(owner=request.user).first()
        if not framework:
            framework = Framework.objects.create(owner=request.user, name="My Priorities")

    all_objectives = Objective.objects.filter(primary_domain__framework=framework).select_related("primary_domain").prefetch_related("whys", "related_domains")
    all_goals = Goal.objects.filter(primary_domain__framework=framework).select_related("primary_domain").prefetch_related("objectives", "related_domains")

    compare_type = request.POST.get("type") or request.GET.get("type", "objectives")
    selected_raw = request.GET.getlist("selected") or request.POST.getlist("selected")
    try:
        selected_ids = [int(x) for x in selected_raw if str(x).isdigit()]
    except (ValueError, TypeError):
        selected_ids = []

    if compare_type == "goals":
        if not selected_ids and all_goals.exists():
            selected_ids = list(all_goals.values_list("id", flat=True)[:2])
        items = all_goals.filter(id__in=selected_ids)
    else:
        if not selected_ids and all_objectives.exists():
            selected_ids = list(all_objectives.values_list("id", flat=True)[:2])
        items = all_objectives.filter(id__in=selected_ids)

    comparison_reflection = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "convert_to_decision":
            title = f"Priority Comparison: {' vs '.join([item.title for item in items][:2])}"
            proposal = f"Evaluating trade-offs and competing demands between: {', '.join([item.title for item in items])}."
            rec = DecisionRecord.objects.create(
                framework=framework,
                title=title[:200],
                proposal_description=proposal,
            )
            for item in items:
                rec.affected_domains.add(item.primary_domain)
                for rd in item.related_domains.all():
                    rec.affected_domains.add(rd)
                if compare_type == "objectives":
                    for w in item.whys.all():
                        rec.relevant_whys.add(w)
                    rec.supporting_objectives.add(item)
                elif compare_type == "goals":
                    for obj in item.objectives.all():
                        rec.supporting_objectives.add(obj)
                        for w in obj.whys.all():
                            rec.relevant_whys.add(w)
            messages.success(request, f"Created draft Decision Assessment from priority comparison.")
            return redirect("decisions:decision_edit", decision_id=rec.id)

        elif action == "reflect":
            llm_config = getattr(request.user, "llm_config", None)
            if not llm_config or not llm_config.consent_given:
                messages.error(request, "Please grant consent in LLM Settings before querying external providers.")
                return redirect("accounts:settings")

            # Build markdown summary of compared items
            summary_lines = [f"# Priority Comparison in {framework.name}\n"]
            for item in items:
                summary_lines.append(f"## {compare_type.title()[:-1]}: {item.title}")
                summary_lines.append(f"- **Primary Domain:** {item.primary_domain.name}")
                summary_lines.append(f"- **Status:** {item.get_status_display()}")
                if compare_type == "objectives":
                    whys_list = [f"{w.title} {'[NON-NEGOTIABLE]' if w.is_non_negotiable else ''}" for w in item.whys.all()]
                    summary_lines.append(f"- **Connected Whys:** {', '.join(whys_list) or 'None'}")
                elif compare_type == "goals":
                    objs_list = [o.title for o in item.objectives.all()]
                    summary_lines.append(f"- **Parent Objectives:** {', '.join(objs_list) or 'None'}")
                    if item.target_date:
                        summary_lines.append(f"- **Target Date:** {item.target_date}")
                rel_doms = [d.name for d in item.related_domains.all()]
                summary_lines.append(f"- **Related Domains:** {', '.join(rel_doms) or 'None'}")
                if item.description:
                    summary_lines.append(f"- **Description:** {item.description}")
                summary_lines.append("")

            comp_md = "\n".join(summary_lines)
            user_prompt = request.POST.get("prompt", "Analyze qualitative tensions and trade-offs between these competing priorities across domains, especially regarding limited time and energy. Note any non-negotiable Whys.")
            success, response_text = generate_reflection(
                user_context_markdown=comp_md,
                user_prompt=user_prompt,
                provider=llm_config.provider,
                model_name=llm_config.model_name,
                api_key=llm_config.api_key,
                api_base=llm_config.api_base,
            )
            if success:
                LLMReflectionLog.objects.create(
                    framework=framework,
                    user_prompt=user_prompt,
                    context_snapshot=comp_md,
                    llm_response=response_text,
                    provider_used=f"{llm_config.provider} ({llm_config.model_name})",
                )
                comparison_reflection = response_text
                messages.success(request, "Thinking partner reflection generated.")
            else:
                messages.error(request, response_text)

    llm_config = getattr(request.user, "llm_config", None)
    return render(request, "decisions/compare.html", {
        "framework": framework,
        "compare_type": compare_type,
        "all_objectives": all_objectives,
        "all_goals": all_goals,
        "selected_ids": selected_ids,
        "items": items,
        "comparison_reflection": comparison_reflection,
        "llm_config": llm_config,
    })
