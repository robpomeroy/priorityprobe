from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from frameworks.models import Framework, Domain
from decisions.models import DecisionRecord, LLMReflectionLog
from exports.services import generate_framework_markdown, generate_decision_markdown
from llm.service import generate_reflection, GUIDED_MODES

@login_required
def chat_view(request, framework_id):
    framework = get_object_or_404(Framework, id=framework_id, owner=request.user)
    llm_config = getattr(request.user, "llm_config", None)
    reflections = LLMReflectionLog.objects.filter(framework=framework, decision__isnull=True).order_by("-created_at")
    all_domains = framework.domains.all()
    all_decisions = DecisionRecord.objects.filter(framework=framework)

    if request.method == "POST":
        if not llm_config or not llm_config.consent_given:
            messages.error(request, "Please grant consent in LLM Settings before querying external providers.")
            return redirect("accounts:settings")

        user_prompt = request.POST.get("prompt", "")
        if not user_prompt.strip():
            messages.warning(request, "Please enter a question or reflection prompt.")
            return redirect("llm:chat", framework_id=framework.id)

        # User-selected context filters
        domains_filter_active = "context_filter_active" in request.POST or "selected_domains" in request.POST
        selected_domain_raw = request.POST.getlist("selected_domains")
        selected_decision_raw = request.POST.getlist("selected_decisions")
        include_history = request.POST.get("include_history") == "1"

        if domains_filter_active:
            try:
                selected_domain_ids = [int(x) for x in selected_domain_raw if str(x).isdigit()]
            except (ValueError, TypeError):
                selected_domain_ids = []
        else:
            selected_domain_ids = None

        context_md = generate_framework_markdown(
            framework,
            include_instructions=True,
            selected_domain_ids=selected_domain_ids
        )

        if selected_decision_raw:
            try:
                selected_decision_ids = [int(x) for x in selected_decision_raw if str(x).isdigit()]
                decs = DecisionRecord.objects.filter(id__in=selected_decision_ids, framework=framework).prefetch_related(
                    "affected_domains", "relevant_whys", "supporting_objectives", "conflicting_objectives"
                )
                if decs.exists():
                    context_md += "\n\n# Selected Decision Assessments Context:\n"
                    for d in decs:
                        context_md += f"\n{generate_decision_markdown(d, include_instructions=False)}\n"
            except (ValueError, TypeError):
                pass

        history = []
        if include_history:
            recent_refs = list(reflections[:2])
            for r in reversed(recent_refs):
                if r.context_snapshot:
                    user_content = f"Here is my current Priorities Framework context:\n\n{r.context_snapshot}\n\nUser Question/Scenario:\n{r.user_prompt}"
                else:
                    user_content = r.user_prompt
                history.append({"role": "user", "content": user_content})
                history.append({"role": "assistant", "content": r.llm_response})

        success, response_text = generate_reflection(
            user_context_markdown=context_md,
            user_prompt=user_prompt,
            provider=llm_config.provider,
            model_name=llm_config.model_name,
            api_key=llm_config.api_key,
            api_base=llm_config.api_base,
            history=history if history else None,
        )

        if success:
            LLMReflectionLog.objects.create(
                framework=framework,
                user_prompt=user_prompt,
                context_snapshot=context_md,
                llm_response=response_text,
                provider_used=f"{llm_config.provider} ({llm_config.model_name})",
            )
            messages.success(request, "Received perspective from thinking partner.")
        else:
            messages.error(request, response_text)

        return redirect("llm:chat", framework_id=framework.id)

    # Initial preview of full context
    preview_context_md = generate_framework_markdown(framework, include_instructions=True)

    return render(request, "llm/chat.html", {
        "framework": framework,
        "llm_config": llm_config,
        "reflections": reflections,
        "all_domains": all_domains,
        "all_decisions": all_decisions,
        "guided_modes": GUIDED_MODES,
        "preview_context_md": preview_context_md,
    })

@login_required
def reflection_delete_view(request, reflection_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    ref = get_object_or_404(LLMReflectionLog, id=reflection_id, framework__owner=request.user)
    fw_id = ref.framework_id
    ref.delete()
    messages.info(request, "Reflection entry deleted.")
    return redirect("llm:chat", framework_id=fw_id)
