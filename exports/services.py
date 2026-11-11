from frameworks.models import Framework, Domain, Why, Objective, Goal
from decisions.models import DecisionRecord
from llm.service import SYSTEM_FACILITATOR_PROMPT

def generate_framework_markdown(framework: Framework, include_instructions: bool = True, selected_domain_ids: list = None) -> str:
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

    domains = framework.domains.all()
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

    return "\n".join(lines)

def generate_decision_markdown(decision: DecisionRecord) -> str:
    """Generates Markdown for a specific Decision Record and its cross-domain links."""
    lines = [
        f"# Decision Assessment: {decision.title}",
        f"**Status:** {decision.get_status_display()}",
        f"**Framework:** {decision.framework.name}",
        "",
        "## Proposal / Opportunity",
        decision.proposal_description,
        "",
        "## Affected Domains",
    ]
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
