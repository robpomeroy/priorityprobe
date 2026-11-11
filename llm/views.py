from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from frameworks.models import Framework
from decisions.models import LLMReflectionLog
from exports.services import generate_framework_markdown
from llm.service import generate_reflection

@login_required
def chat_view(request, framework_id):
    framework = get_object_or_404(Framework, id=framework_id, owner=request.user)
    llm_config = getattr(request.user, "llm_config", None)
    reflections = LLMReflectionLog.objects.filter(framework=framework, decision__isnull=True).order_by("-created_at")

    if request.method == "POST":
        if not llm_config or not llm_config.consent_given:
            messages.error(request, "Please grant consent in LLM Settings before querying external providers.")
            return redirect("accounts:settings")

        user_prompt = request.POST.get("prompt", "")
        if not user_prompt.strip():
            messages.warning(request, "Please enter a question or reflection prompt.")
            return redirect("llm:chat", framework_id=framework.id)

        context_md = generate_framework_markdown(framework, include_instructions=True)
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

    return render(request, "llm/chat.html", {
        "framework": framework,
        "llm_config": llm_config,
        "reflections": reflections,
    })
