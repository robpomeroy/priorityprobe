from frameworks.models import Framework, Domain, Why, Objective, Goal, StatusChoices

def seed_sample_framework(user) -> Framework:
    """Populates an illustrative sample framework clearly flagged with is_sample=True."""
    framework = Framework.objects.create(
        owner=user,
        name="Sample Life & Priorities Framework",
        description="Illustrative starter framework demonstrating Domains, Whys, Objectives, and Goals.",
        is_sample=True,
    )

    # Domain 1: Family and Home
    family = Domain.objects.create(
        framework=framework,
        name="Family and Home",
        description="Broad sphere covering domestic stability, relationships, and caring responsibilities.",
        display_order=1,
        is_sample=True,
    )
    why_family_1 = Why.objects.create(
        domain=family,
        title="To provide a secure and loving home for my family.",
        description="Core conviction that loved ones need warmth, emotional presence, and safety.",
        is_non_negotiable=True,
        display_order=1,
        is_sample=True,
    )
    why_family_2 = Why.objects.create(
        domain=family,
        title="To be present and actively involved in everyday family life.",
        description="Ensuring career or side interests do not crowd out unhurried time together.",
        is_non_negotiable=False,
        display_order=2,
        is_sample=True,
    )

    # Domain 2: Work and Vocation
    work = Domain.objects.create(
        framework=framework,
        name="Work and Vocation",
        description="Professional contribution, skills development, and financial stewardship.",
        display_order=2,
        is_sample=True,
    )
    why_work_1 = Why.objects.create(
        domain=work,
        title="To contribute something worthwhile and intellectually honest through my work.",
        description="Finding meaning in craft, integrity, and serving real human needs.",
        is_non_negotiable=False,
        display_order=1,
        is_sample=True,
    )
    why_work_2 = Why.objects.create(
        domain=work,
        title="To provide financial resilience and support family independence.",
        description="Earning reliably to meet responsibilities without reckless overcommitment.",
        is_non_negotiable=True,
        display_order=2,
        is_sample=True,
    )

    # Domain 3: Personal Health and Well-being
    health = Domain.objects.create(
        framework=framework,
        name="Personal Health and Well-being",
        description="Physical endurance, mental clarity, rest, and renewal.",
        display_order=3,
        is_sample=True,
    )
    why_health = Why.objects.create(
        domain=health,
        title="To steward physical and mental health to sustain other commitments.",
        description="Recognizing that energy and health are foundations for everything else.",
        is_non_negotiable=False,
        display_order=1,
        is_sample=True,
    )

    # Objectives
    obj_financial = Objective.objects.create(
        primary_domain=work,
        title="Build financial resilience and a stable home environment.",
        description="Create margin against unexpected crises or downturns.",
        status=StatusChoices.ACTIVE,
        is_sample=True,
    )
    obj_financial.whys.add(why_family_1, why_work_2)
    obj_financial.related_domains.add(family)

    obj_family_time = Objective.objects.create(
        primary_domain=family,
        title="Protect consistent, unhurried time with family each week.",
        description="Maintain clear boundaries between work hours and home life.",
        status=StatusChoices.ACTIVE,
        is_sample=True,
    )
    obj_family_time.whys.add(why_family_2)
    obj_family_time.related_domains.add(work)

    obj_fitness = Objective.objects.create(
        primary_domain=health,
        title="Sustain cardiovascular fitness and regular rest cycles.",
        description="Maintain energy levels through routine movement and decent sleep.",
        status=StatusChoices.ACTIVE,
        is_sample=True,
    )
    obj_fitness.whys.add(why_health)

    # Goals
    goal_fund = Goal.objects.create(
        primary_domain=work,
        title="Establish an emergency buffer of £10,000 over two years.",
        description="Save regularly into a high-yield liquid account.",
        status=StatusChoices.ACTIVE,
        is_sample=True,
    )
    goal_fund.objectives.add(obj_financial)
    goal_fund.related_domains.add(family)

    goal_evenings = Goal.objects.create(
        primary_domain=family,
        title="Protect two work-free evenings each week for dinner and connection.",
        description="Close laptop by 6:00pm on Tuesdays and Thursdays.",
        status=StatusChoices.ACTIVE,
        is_sample=True,
    )
    goal_evenings.objectives.add(obj_family_time)
    goal_evenings.related_domains.add(work)

    return framework

def remove_sample_frameworks(user) -> int:
    """Removes all sample frameworks and items owned by the user."""
    deleted_count, _ = Framework.objects.filter(owner=user, is_sample=True).delete()
    return deleted_count
