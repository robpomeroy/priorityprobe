from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from frameworks.models import Framework, Domain, Why, Objective, Goal, StatusChoices
from frameworks.forms import FrameworkForm, DomainForm, WhyForm, ObjectiveForm, GoalForm
from frameworks.services import seed_sample_framework, remove_sample_frameworks

def _get_user_framework(user, framework_id=None):
    if framework_id:
        return get_object_or_404(Framework, id=framework_id, owner=user)
    fw = Framework.objects.filter(owner=user).first()
    if not fw:
        fw = Framework.objects.create(owner=user, name="My Personal Priorities")
    return fw

@login_required
def workspace_view(request, framework_id=None):
    framework = _get_user_framework(request.user, framework_id)
    user_frameworks = Framework.objects.filter(owner=request.user)
    domains = framework.domains.prefetch_related(
        "whys", "primary_objectives__whys", "primary_objectives__related_domains",
        "primary_goals__objectives", "primary_goals__related_domains"
    ).all()
    
    return render(request, "frameworks/workspace.html", {
        "framework": framework,
        "user_frameworks": user_frameworks,
        "domains": domains,
    })

@login_required
def seed_sample_view(request):
    if request.method == "POST":
        fw = seed_sample_framework(request.user)
        messages.success(request, f"Loaded sample framework '{fw.name}'. You can modify or remove it anytime.")
        return redirect("frameworks:workspace_detail", framework_id=fw.id)
    return redirect("frameworks:workspace")

@login_required
def remove_sample_view(request):
    if request.method == "POST":
        count = remove_sample_frameworks(request.user)
        messages.info(request, f"Removed {count} sample framework(s).")
        return redirect("frameworks:workspace")
    return redirect("frameworks:workspace")

@login_required
def domain_create_view(request, framework_id):
    framework = get_object_or_404(Framework, id=framework_id, owner=request.user)
    if request.method == "POST":
        form = DomainForm(request.POST)
        if form.is_valid():
            domain = form.save(commit=False)
            domain.framework = framework
            domain.save()
            messages.success(request, f"Added domain '{domain.name}'.")
            return redirect("frameworks:workspace_detail", framework_id=framework.id)
    else:
        form = DomainForm()
    return render(request, "frameworks/form_modal.html", {"form": form, "title": "Add New Domain"})

@login_required
def domain_edit_view(request, domain_id):
    domain = get_object_or_404(Domain, id=domain_id, framework__owner=request.user)
    if request.method == "POST":
        form = DomainForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated domain '{domain.name}'.")
            return redirect("frameworks:workspace_detail", framework_id=domain.framework_id)
    else:
        form = DomainForm(instance=domain)
    return render(request, "frameworks/form_modal.html", {"form": form, "title": f"Edit Domain: {domain.name}"})

@login_required
def domain_delete_view(request, domain_id):
    domain = get_object_or_404(Domain, id=domain_id, framework__owner=request.user)
    fw_id = domain.framework_id
    if request.method == "POST":
        name = domain.name
        domain.delete()
        messages.info(request, f"Domain '{name}' and its child items were deleted.")
        return redirect("frameworks:workspace_detail", framework_id=fw_id)
    return render(request, "frameworks/confirm_delete.html", {"item_type": "Domain", "item_name": domain.name})

@login_required
def why_create_view(request, domain_id):
    domain = get_object_or_404(Domain, id=domain_id, framework__owner=request.user)
    if request.method == "POST":
        form = WhyForm(request.POST)
        if form.is_valid():
            why = form.save(commit=False)
            why.domain = domain
            why.save()
            messages.success(request, "Added Why.")
            return redirect("frameworks:workspace_detail", framework_id=domain.framework_id)
    else:
        form = WhyForm()
    return render(request, "frameworks/form_modal.html", {
        "form": form,
        "title": f"Add Why in {domain.name}",
        "guidance": "Why does this area matter to you? Why should anything happen here?",
    })

@login_required
def why_edit_view(request, why_id):
    why = get_object_or_404(Why, id=why_id, domain__framework__owner=request.user)
    if request.method == "POST":
        form = WhyForm(request.POST, instance=why)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated Why.")
            return redirect("frameworks:workspace_detail", framework_id=why.domain.framework_id)
    else:
        form = WhyForm(instance=why)
    return render(request, "frameworks/form_modal.html", {"form": form, "title": "Edit Why"})

@login_required
def why_delete_view(request, why_id):
    why = get_object_or_404(Why, id=why_id, domain__framework__owner=request.user)
    fw_id = why.domain.framework_id
    if request.method == "POST":
        why.delete()
        messages.info(request, "Why deleted.")
        return redirect("frameworks:workspace_detail", framework_id=fw_id)
    return render(request, "frameworks/confirm_delete.html", {"item_type": "Why", "item_name": why.title})

@login_required
def objective_create_view(request, framework_id):
    framework = get_object_or_404(Framework, id=framework_id, owner=request.user)
    initial_domain_id = request.GET.get("domain_id")
    initial = {"primary_domain": initial_domain_id} if initial_domain_id else {}
    if request.method == "POST":
        form = ObjectiveForm(request.POST, framework=framework)
        if form.is_valid():
            form.save()
            messages.success(request, "Created objective.")
            return redirect("frameworks:workspace_detail", framework_id=framework.id)
    else:
        form = ObjectiveForm(framework=framework, initial=initial)
    return render(request, "frameworks/form_modal.html", {
        "form": form,
        "title": "Add New Objective",
        "guidance": "What would you like your Whys to lead to?",
    })

@login_required
def objective_edit_view(request, objective_id):
    objective = get_object_or_404(Objective, id=objective_id, primary_domain__framework__owner=request.user)
    framework = objective.primary_domain.framework
    if request.method == "POST":
        form = ObjectiveForm(request.POST, instance=objective, framework=framework)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated objective.")
            return redirect("frameworks:workspace_detail", framework_id=framework.id)
    else:
        form = ObjectiveForm(instance=objective, framework=framework)
    return render(request, "frameworks/form_modal.html", {"form": form, "title": "Edit Objective"})

@login_required
def objective_delete_view(request, objective_id):
    objective = get_object_or_404(Objective, id=objective_id, primary_domain__framework__owner=request.user)
    fw_id = objective.primary_domain.framework_id
    if request.method == "POST":
        objective.delete()
        messages.info(request, "Objective deleted.")
        return redirect("frameworks:workspace_detail", framework_id=fw_id)
    return render(request, "frameworks/confirm_delete.html", {"item_type": "Objective", "item_name": objective.title})

@login_required
def goal_create_view(request, framework_id):
    framework = get_object_or_404(Framework, id=framework_id, owner=request.user)
    initial_domain_id = request.GET.get("domain_id")
    initial = {"primary_domain": initial_domain_id} if initial_domain_id else {}
    if request.method == "POST":
        form = GoalForm(request.POST, framework=framework)
        if form.is_valid():
            form.save()
            messages.success(request, "Created goal.")
            return redirect("frameworks:workspace_detail", framework_id=framework.id)
    else:
        form = GoalForm(framework=framework, initial=initial)
    return render(request, "frameworks/form_modal.html", {
        "form": form,
        "title": "Add New Goal",
        "guidance": "What specifically will you do or achieve?",
    })

@login_required
def goal_edit_view(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, primary_domain__framework__owner=request.user)
    framework = goal.primary_domain.framework
    if request.method == "POST":
        form = GoalForm(request.POST, instance=goal, framework=framework)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated goal.")
            return redirect("frameworks:workspace_detail", framework_id=framework.id)
    else:
        form = GoalForm(instance=goal, framework=framework)
    return render(request, "frameworks/form_modal.html", {"form": form, "title": "Edit Goal"})

@login_required
def goal_delete_view(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, primary_domain__framework__owner=request.user)
    fw_id = goal.primary_domain.framework_id
    if request.method == "POST":
        goal.delete()
        messages.info(request, "Goal deleted.")
        return redirect("frameworks:workspace_detail", framework_id=fw_id)
    return render(request, "frameworks/confirm_delete.html", {"item_type": "Goal", "item_name": goal.title})

from datetime import timedelta

@login_required
def domain_move_view(request, domain_id, direction):
    if request.method != "POST":
        return HttpResponseForbidden()
    domain = get_object_or_404(Domain, id=domain_id, framework__owner=request.user)
    fw = domain.framework
    all_domains = list(fw.domains.order_by("display_order", "id"))
    idx = all_domains.index(domain)

    if direction == "up" and idx > 0:
        prev_domain = all_domains[idx - 1]
        domain.display_order, prev_domain.display_order = prev_domain.display_order, domain.display_order
        if domain.display_order == prev_domain.display_order:
            domain.display_order -= 1
        domain.save()
        prev_domain.save()
    elif direction == "down" and idx < len(all_domains) - 1:
        next_domain = all_domains[idx + 1]
        domain.display_order, next_domain.display_order = next_domain.display_order, domain.display_order
        if domain.display_order == next_domain.display_order:
            domain.display_order += 1
        domain.save()
        next_domain.save()

    return redirect("frameworks:workspace_detail", framework_id=fw.id)

@login_required
def why_move_view(request, why_id, direction):
    if request.method != "POST":
        return HttpResponseForbidden()
    why = get_object_or_404(Why, id=why_id, domain__framework__owner=request.user)
    all_whys = list(why.domain.whys.order_by("display_order", "id"))
    idx = all_whys.index(why)

    if direction == "up" and idx > 0:
        prev_why = all_whys[idx - 1]
        why.display_order, prev_why.display_order = prev_why.display_order, why.display_order
        if why.display_order == prev_why.display_order:
            why.display_order -= 1
        why.save()
        prev_why.save()
    elif direction == "down" and idx < len(all_whys) - 1:
        next_why = all_whys[idx + 1]
        why.display_order, next_why.display_order = next_why.display_order, why.display_order
        if why.display_order == next_why.display_order:
            why.display_order += 1
        why.save()
        next_why.save()

    return redirect("frameworks:workspace_detail", framework_id=why.domain.framework_id)

@login_required
def objective_status_view(request, objective_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    obj = get_object_or_404(Objective, id=objective_id, primary_domain__framework__owner=request.user)
    new_status = request.POST.get("status")
    if new_status in StatusChoices.values:
        obj.status = new_status
        obj.save()
        messages.success(request, f"Objective status changed to {obj.get_status_display()}.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("frameworks:workspace_detail", framework_id=obj.primary_domain.framework_id)

@login_required
def goal_status_view(request, goal_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    goal = get_object_or_404(Goal, id=goal_id, primary_domain__framework__owner=request.user)
    new_status = request.POST.get("status")
    if new_status in StatusChoices.values:
        goal.status = new_status
        goal.save()
        messages.success(request, f"Goal status changed to {goal.get_status_display()}.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("frameworks:workspace_detail", framework_id=goal.primary_domain.framework_id)

@login_required
def review_view(request, framework_id=None):
    framework = _get_user_framework(request.user, framework_id)
    status_filter = request.GET.get("status", "")
    age_filter = request.GET.get("age", "")
    today = timezone.now().date()
    
    whys = Why.objects.filter(domain__framework=framework).select_related("domain")
    objectives = Objective.objects.filter(primary_domain__framework=framework).select_related("primary_domain")
    goals = Goal.objects.filter(primary_domain__framework=framework).select_related("primary_domain")
    
    if status_filter:
        objectives = objectives.filter(status=status_filter)
        goals = goals.filter(status=status_filter)

    if age_filter == "never":
        whys = whys.filter(last_reviewed_at__isnull=True)
        objectives = objectives.filter(last_reviewed_at__isnull=True)
        goals = goals.filter(last_reviewed_at__isnull=True)
    elif age_filter in ("90", "180", "365"):
        days = int(age_filter)
        cutoff = today - timedelta(days=days)
        whys = whys.filter(last_reviewed_at__isnull=False, last_reviewed_at__lt=cutoff)
        objectives = objectives.filter(last_reviewed_at__isnull=False, last_reviewed_at__lt=cutoff)
        goals = goals.filter(last_reviewed_at__isnull=False, last_reviewed_at__lt=cutoff)

    return render(request, "frameworks/review.html", {
        "framework": framework,
        "whys": whys,
        "objectives": objectives,
        "goals": goals,
        "status_filter": status_filter,
        "age_filter": age_filter,
        "StatusChoices": StatusChoices,
    })

@login_required
def mark_all_reviewed_view(request, framework_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    framework = get_object_or_404(Framework, id=framework_id, owner=request.user)
    today = timezone.now().date()
    Why.objects.filter(domain__framework=framework).update(last_reviewed_at=today)
    Objective.objects.filter(primary_domain__framework=framework).update(last_reviewed_at=today)
    Goal.objects.filter(primary_domain__framework=framework).update(last_reviewed_at=today)
    messages.success(request, f"Marked all framework items as reviewed on {today}.")
    return redirect("frameworks:review_detail", framework_id=framework.id)

@login_required
def mark_reviewed_view(request, item_type, item_id):
    if request.method == "POST":
        today = timezone.now().date()
        if item_type == "why":
            item = get_object_or_404(Why, id=item_id, domain__framework__owner=request.user)
        elif item_type == "objective":
            item = get_object_or_404(Objective, id=item_id, primary_domain__framework__owner=request.user)
        elif item_type == "goal":
            item = get_object_or_404(Goal, id=item_id, primary_domain__framework__owner=request.user)
        else:
            return HttpResponseForbidden()
        item.last_reviewed_at = today
        item.save()
        if request.headers.get("HX-Request"):
            return HttpResponse(f"<span class='badge bg-sage text-white'>Reviewed {today}</span>")
        messages.success(request, f"Marked as reviewed on {today}.")
        return redirect("frameworks:review_detail", framework_id=item.domain.framework_id if hasattr(item, "domain") else item.primary_domain.framework_id)
    return HttpResponseForbidden()
