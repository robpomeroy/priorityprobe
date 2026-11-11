import re
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.text import slugify
from frameworks.models import Framework
from decisions.models import DecisionRecord
from exports.services import generate_framework_markdown, generate_decision_markdown

def sanitize_filename(name: str, fallback: str = "export") -> str:
    """Sanitizes user input to create a safe ASCII filename component for Content-Disposition."""
    cleaned = slugify(name)
    if not cleaned:
        cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', name).strip('_')
    return cleaned or fallback

@login_required
def export_framework_view(request, framework_id):
    framework = get_object_or_404(Framework, id=framework_id, owner=request.user)
    include_instructions = request.GET.get("instructions", "1") == "1"
    md_content = generate_framework_markdown(framework, include_instructions=include_instructions)

    if request.GET.get("download"):
        response = HttpResponse(md_content, content_type="text/markdown; charset=utf-8")
        safe_name = sanitize_filename(framework.name, "framework")
        filename = f"prioritysuite_{safe_name}.md"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    return render(request, "exports/export_preview.html", {
        "title": f"Markdown Export: {framework.name}",
        "markdown_content": md_content,
        "framework": framework,
    })

@login_required
def export_decision_view(request, decision_id):
    decision = get_object_or_404(DecisionRecord, id=decision_id, framework__owner=request.user)
    md_content = generate_decision_markdown(decision)

    if request.GET.get("download"):
        response = HttpResponse(md_content, content_type="text/markdown; charset=utf-8")
        safe_title = sanitize_filename(decision.title, "decision")
        filename = f"decision_{safe_title}.md"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    return render(request, "exports/export_preview.html", {
        "title": f"Decision Assessment Export: {decision.title}",
        "markdown_content": md_content,
        "decision": decision,
    })
