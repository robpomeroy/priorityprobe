from frameworks.models import Framework, Domain, Why, Objective, Goal
from decisions.models import DecisionRecord
from llm.service import SYSTEM_FACILITATOR_PROMPT

def generate_framework_markdown(
    framework: Framework,
    include_instructions: bool = True,
    selected_domain_ids: list = None,
    selected_decision_ids: list = None,
    include_reflections: bool = False,
) -> str:
    """Generates clean Markdown for a user's framework, including prompt instructions for external LLMs."""
    lines = []

    if include_instructions:
        lines.append("# PrioritySuite — Personal Priorities & Facilitator Context")
        lines.append("")
        lines.append("## Facilitator Instructions for LLM")
        lines.append(SYSTEM_FACILITATOR_PROMPT.strip())
        lines.append("\n---\n")

    lines.append(f"# Framework: {framework.name}")
    if framework.description:
        lines.append(f"> {framework.description}\n")

    domains = framework.domains.prefetch_related(
        "whys",
        "primary_objectives__related_domains",
        "primary_goals__related_domains",
    ).all()
    if selected_domain_ids is not None:
        domains = domains.filter(id__in=selected_domain_ids)

    for domain in domains:
        lines.append(f"## Domain: {domain.name}")
        if domain.description:
            lines.append(f"*{domain.description}*\n")

        # Whys
        whys = domain.whys.all()
        if whys.exists():
            lines.append("### Whys (Enduring Foundations)")
            for why in whys:
                nn_badge = " **[NON-NEGOTIABLE]**" if why.is_non_negotiable else ""
                lines.append(f"- **{why.title}**{nn_badge}")
                if why.description:
                    lines.append(f"  - {why.description}")
            lines.append("")

        # Objectives
        objectives = domain.primary_objectives.all()
        if objectives.exists():
            lines.append("### Objectives")
            for obj in objectives:
                status_badge = f" `[{obj.get_status_display()}]`"
                rel_domains = ", ".join([d.name for d in obj.related_domains.all()])
                rel_str = f" *(Related to: {rel_domains})*" if rel_domains else ""
                lines.append(f"- **{obj.title}**{status_badge}{rel_str}")
                if obj.description:
                    lines.append(f"  - {obj.description}")
            lines.append("")

        # Goals
        goals = domain.primary_goals.all()
        if goals.exists():
            lines.append("### Goals")
            for goal in goals:
                status_badge = f" `[{goal.get_status_display()}]`"
                date_str = f" *(Target: {goal.target_date})*" if goal.target_date else ""
                lines.append(f"- **{goal.title}**{status_badge}{date_str}")
                if goal.description:
                    lines.append(f"  - {goal.description}")
            lines.append("")

        lines.append("---")

    # Optional selected decision assessments
    if selected_decision_ids:
        decs = DecisionRecord.objects.filter(id__in=selected_decision_ids, framework=framework).prefetch_related(
            "affected_domains", "relevant_whys", "supporting_objectives", "conflicting_objectives"
        )
        if decs.exists():
            lines.append("\n# Cross-Domain Decision Assessments\n")
            for dec in decs:
                lines.append(f"## Decision: {dec.title}")
                lines.append(f"**Status:** {dec.get_status_display()}")
                lines.append(f"\n**Proposal / Opportunity:**\n{dec.proposal_description}\n")
                if dec.benefits_and_costs:
                    lines.append(f"**Benefits and Costs Considered:**\n{dec.benefits_and_costs}\n")
                if dec.unresolved_questions:
                    lines.append(f"**Unresolved Questions & Assumptions:**\n{dec.unresolved_questions}\n")
                if dec.decision_outcome:
                    lines.append(f"**Outcome / Decision Made:**\n{dec.decision_outcome}\n")
                lines.append("---")

    # Optional saved thinking partner reflections
    if include_reflections:
        from decisions.models import LLMReflectionLog
        refs = LLMReflectionLog.objects.filter(framework=framework, decision__isnull=True).order_by("-created_at")[:5]
        if refs.exists():
            lines.append("\n# Saved Thinking Partner Reflections\n")
            for r in refs:
                date_str = r.created_at.strftime('%Y-%m-%d') if r.created_at else "Undated"
                lines.append(f"### Reflection ({date_str})")
                lines.append(f"**Prompt:** {r.user_prompt}")
                lines.append(f"\n{r.llm_response}\n")
                lines.append("---")

    return "\n".join(lines)

def generate_decision_markdown(decision: DecisionRecord, include_instructions: bool = True) -> str:
    """Generates Markdown for a specific Decision Record and its cross-domain links."""
    lines = []

    if include_instructions:
        lines.append("# PrioritySuite — Decision Assessment & Facilitator Context")
        lines.append("")
        lines.append("## Facilitator Instructions for LLM")
        lines.append(SYSTEM_FACILITATOR_PROMPT.strip())
        lines.append("\n---\n")

    lines.extend([
        f"# Decision Assessment: {decision.title}",
        f"**Status:** {decision.get_status_display()}",
        f"**Framework:** {decision.framework.name}",
        "",
        "## Proposal / Opportunity",
        decision.proposal_description,
        "",
        "## Affected Domains",
    ])
    aff = decision.affected_domains.all()
    if aff.exists():
        for d in aff:
            lines.append(f"- {d.name}")
    else:
        lines.append("- *(None specified)*")

    lines.append("\n## Relevant Whys")
    whys = decision.relevant_whys.all()
    if whys.exists():
        for w in whys:
            nn = " [NON-NEGOTIABLE]" if w.is_non_negotiable else ""
            lines.append(f"- {w.title} ({w.domain.name}){nn}")
    else:
        lines.append("- *(None specified)*")

    lines.append("\n## Supporting Objectives")
    sup = decision.supporting_objectives.all()
    if sup.exists():
        for o in sup:
            lines.append(f"- {o.title} ({o.primary_domain.name})")
    else:
        lines.append("- *(None specified)*")

    lines.append("\n## Conflicting Objectives / Tensions")
    conf = decision.conflicting_objectives.all()
    if conf.exists():
        for o in conf:
            lines.append(f"- {o.title} ({o.primary_domain.name})")
    else:
        lines.append("- *(None specified)*")

    if decision.benefits_and_costs:
        lines.extend(["\n## Benefits & Costs / Trade-offs", decision.benefits_and_costs])

    if decision.alternatives_considered:
        lines.extend(["\n## Alternatives Considered", decision.alternatives_considered])

    if decision.unresolved_questions:
        lines.extend(["\n## Unresolved Questions", decision.unresolved_questions])

    if decision.decision_outcome:
        lines.extend(["\n## Decision & Outcome Reasoning", decision.decision_outcome])

    return "\n".join(lines)
