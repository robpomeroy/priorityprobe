# PrioritySuite Specification

## Personal Priorities and Decision-Making Framework

**Purpose:** Product and implementation brief for an open-source application
**Primary audience:** Product and engineering contributors, including agents

------------------------------------------------------------------------

## 1. Product purpose

A private, user-led tool to help people:

-   Explore what matters to them and why.
-   Organise their priorities across different areas of life.
-   Turn enduring reasons into meaningful objectives and practical
    goals.
-   Consider new opportunities, commitments and decisions in the context
    of their wider priorities.
-   Use a large language model (LLM) as a thinking partner to explore
    tensions, trade-offs and possible courses of action.

The tool should help people think more clearly, not tell them what to
value or how to live.

**Core principle:** the user defines the framework. The software helps
them examine and apply it.

## 2. Conceptual model

The core structure is:

**Domains → Whys → Objectives → Goals**

  -----------------------------------------------------------------------
  Level                   Meaning                 Typical stability
  ----------------------- ----------------------- -----------------------
  Domain                  A broad sphere or area  Relatively stable
                          of life                 

  Why                     Why that domain         Enduring
                          matters; why anything   
                          should happen within it 

  Objective               What the Whys should    Reviewed periodically
                          lead to                 

  Goal                    What specifically the   More changeable
                          user will do, change or 
                          achieve                 
  -----------------------------------------------------------------------

### 2.1 Domains

Domains are the broad spheres of life through which a person organises
their framework. They should be reasonably stable and not require
frequent adjustment.

Possible examples include:

-   Personal life and development
-   Family and home
-   Faith, church and spiritual life
-   Work and vocation
-   Friendships and other relationships
-   Creativity, recreation and interests
-   Community and wider society

These are suggestions, not a prescribed taxonomy. Users can rename, add,
remove and reorder domains.

### 2.2 Whys

A Why expresses the reason something matters within a domain. It may
express a conviction, value, aspiration, commitment, responsibility or
belief.

The tool should start by asking users to articulate their Whys, rather
than requiring them to identify abstract values first.

Examples:

-   To provide a secure and loving home for my family.
-   To develop and use my abilities well.
-   To live faithfully according to my understanding of God.
-   To contribute something worthwhile through my work.
-   To maintain meaningful friendships.

A domain may contain several Whys. They should be treated as relatively
enduring, although users can revise them when their understanding or
circumstances change.

### 2.3 Objectives

Objectives describe what a person wants their Whys to lead to. They
translate reasons into intended directions or outcomes.

Example:

-   **Why:** To provide a secure and loving home for my family.
-   **Objective:** Build financial resilience and a stable home
    environment.

Objectives should normally be reviewed periodically, perhaps annually,
but the software should not impose a fixed review cycle.

### 2.4 Goals

Goals express specific actions, changes or achievements that contribute
to objectives.

Example:

-   **Objective:** Build financial resilience.
-   **Goal:** Establish an emergency fund of £10,000 over two years.

Goals may be completed, replaced, revised or abandoned. They are
expected to change more frequently than objectives or Whys.

### 2.5 Responsibilities

Responsibilities should be supported as part of the language people use
to express their Whys and objectives. They should not be forced into a
separate category.

A responsibility might arise from a person's values, worldview,
relationships, commitments or circumstances. The user should be free to
describe it in their own terms.

### 2.6 Worldview and faith

The framework must accommodate different relationships between worldview
and everyday life.

For example, a person may:

-   Regard faith or worldview as the overarching basis for all their
    other priorities.
-   Treat faith or worldview as one important domain among several.
-   Express their worldview through Whys in multiple domains.
-   Have no religious or explicitly defined worldview.

The software must not assume one of these arrangements. Users should be
able to organise their framework in whatever way makes sense to them.

## 3. Application organisation

The primary view should be organised by domain, with each domain
displaying its Whys, objectives and goals together.

Example:

### Family and home

**Whys** - To provide a secure and loving home for my family. - To be
present and actively involved in my children's lives.

**Objectives** - Build financial resilience. - Make sufficient time for
family life.

**Goals** - Build an emergency fund of £10,000 over two years. - Protect
two evenings a week for family activities.

This structure should make it easy to understand how practical goals
relate to the reasons behind them.

Objectives and goals should have one primary domain so that the
framework remains straightforward. An objective or goal may also be
relevant to other domains. The initial version should allow users to
record those related domains, without requiring a complex network of
relationships.

The interface should make the distinction between the four levels clear.
It should not require users to understand the underlying data model or
philosophical terminology before they can use the application.

## 4. Cross-domain priorities and decision support

This is an important part of the product, not merely an optional
reporting feature.

A person's domains are displayed separately for clarity, but real
decisions often affect several domains at once. The tool should
therefore support both:

-   **Within-domain thinking:** How well does this objective or goal
    serve the Whys in its own domain?
-   **Across-domain thinking:** What does pursuing this objective or
    goal mean for the person's other priorities?

### 4.1 Assessing a proposed decision

A user should be able to enter a proposed activity, opportunity,
commitment or change and ask the tool to help assess it against their
framework.

Example:

> I have been offered a promotion. It would increase my income and
> provide career development, but it would involve longer hours and more
> travel.

The tool should help the user explore:

1.  Which domains might be affected?
2.  Which Whys are relevant?
3.  Which existing objectives might this support?
4.  Which objectives or Whys might it conflict with?
5.  What are the likely benefits, costs and opportunity costs?
6.  Are there alternative ways of pursuing the same underlying
    objective?
7.  What further information or reflection would help the user decide?

The assessment should identify both positive and negative implications.
It should not assume that every decision must advance every domain.

### 4.2 Comparing priorities

The application should help users compare competing priorities across
domains, especially where time, money, attention or energy are limited.

For example, a decision might advance financial security while reducing
time available for family relationships. The tool should make that
tension visible and help the user examine it.

However, it should not automatically resolve the tension by assigning
numerical weights or calculating an overall score.

Some priorities may be non-negotiable. Some may be more important in
particular circumstances. Some trade-offs may be acceptable, while
others may not be. These are judgements for the user to make.

The tool should therefore support:

-   Qualitative comparison and reflection.
-   Identification of conflicts and competing commitments.
-   Recognition of non-negotiables, if the user chooses to identify
    them.
-   Exploration of consequences and alternatives.
-   Recording the reasoning behind a decision, if desired.

It may offer ways to structure a comparison, but should not present its
conclusions as objective measurements of what the user ought to do.

### 4.3 Decision records

A useful optional feature would allow users to record:

-   The decision or opportunity considered.
-   The relevant domains, Whys and objectives.
-   The main benefits and disadvantages considered.
-   The reasoning behind the decision.
-   The decision made, if one was made.
-   Any assumptions or questions still unresolved.

This would allow users to revisit decisions and learn from them. It
should remain lightweight rather than becoming a compulsory approval or
workflow process.

## 5. Contextual guidance and examples

The application should provide useful explanations wherever users are
asked to enter information.

  -----------------------------------------------------------------------
  Concept                             Guidance shown to the user
  ----------------------------------- -----------------------------------
  Domain                              What broad area of life are you
                                      considering?

  Why                                 Why does this area matter to you?
                                      Why should anything happen here?

  Objective                           What would you like your Why to
                                      lead to?

  Goal                                What specifically will you do or
                                      achieve?
  -----------------------------------------------------------------------

Help should include examples, prompts and questions that help users
articulate their own thinking.

### 5.1 Sample content

On first use, the application should offer to populate the framework
with illustrative examples, including sample domains, Whys, objectives
and goals.

These examples must be:

-   Clearly identified as examples.
-   Editable and removable.
-   Optional, with the ability to start from an empty framework.
-   Varied enough not to imply that one particular lifestyle or
    worldview is expected.

The application should never make sample content appear to be the user's
own stated priorities.

## 6. LLM integration

An LLM should act as a facilitator, sounding board and analytical
assistant. It should not act as an authority on the user's values or
decisions.

### 6.1 Expected capabilities

The LLM should be able to:

-   Help users articulate and refine their Whys.
-   Explore the relationship between Whys, objectives and goals.
-   Identify gaps, ambiguity or apparent contradictions.
-   Help formulate and assess objectives and goals.
-   Examine a proposed decision across multiple domains.
-   Identify tensions and possible trade-offs.
-   Suggest alternative approaches.
-   Ask useful questions rather than prematurely offering conclusions.
-   Help review the framework periodically.

### 6.2 Reliability and transparency

The LLM must distinguish between:

-   What the user has explicitly stated.
-   What the LLM has inferred.
-   What the LLM is suggesting.
-   What remains uncertain or unresolved.

It must not silently turn an inference into an established Why,
objective or user preference.

Example:

> You have said that financial security is important to you. I infer
> that this promotion may support that priority, but I do not yet know
> how you weigh that against your stated desire to spend more time with
> your family.

This distinction is essential to maintaining user control.

### 6.3 User-controlled context

The LLM should be given relevant framework information, including:

-   Domains.
-   Whys.
-   Objectives and their status.
-   Goals and their status.
-   Relevant related domains.
-   Any user-defined non-negotiables or decision notes.
-   Unresolved questions, where relevant.

Users should be able to choose what information is shared in an LLM
conversation.

### 6.4 Bring your own key and provider flexibility

The application should support a Bring Your Own Key (BYOK) approach,
allowing users to connect to supported LLM providers.

The architecture should make it possible to add providers without
changing the core application. Initial candidates include:

-   OpenAI
-   Anthropic
-   Google Gemini
-   Locally hosted models, such as Ollama

Provider availability and capabilities will vary, so the application
should clearly communicate which features are supported by each
connection.

### 6.5 Exporting the framework for external LLM use

A core feature should be the ability to export the framework as
Markdown.

The export should include:

-   The user's framework and its structure.
-   A concise explanation of the model.
-   Instructions for an LLM to act as a facilitator rather than an
    authority.
-   Guidance to distinguish explicit statements from inferences and
    suggestions.
-   The user's actual Whys, objectives and goals.
-   Any relevant decision notes or unresolved questions selected for
    export.

This should allow a user to paste the export into an external LLM, along
with a question or scenario, without needing to use the application's
own LLM integration.

## 7. Functional requirements

  -----------------------------------------------------------------------
  Area                                Required functionality
  ----------------------------------- -----------------------------------
  Framework                           Create, edit, export and delete a
                                      personal framework

  Domains                             Add, edit, delete and reorder
                                      domains

  Whys                                Add, edit and remove multiple Whys
                                      within a domain

  Objectives                          Create objectives within a primary
                                      domain and optionally link them to
                                      one or more Whys

  Goals                               Create goals within a primary
                                      domain and optionally link them to
                                      one or more objectives

  Related domains                     Identify other domains affected by
                                      an objective or goal

  Status                              Track objectives and goals as
                                      active, completed, paused or
                                      abandoned, as appropriate

  Review                              Support periodic review of Whys,
                                      objectives and goals

  Decision support                    Assess proposed decisions against
                                      relevant priorities across domains

  Decision records                    Optionally record the reasoning and
                                      outcome of decisions

  Guidance                            Provide contextual explanations,
                                      prompts and sample content

  LLM                                 Support framework discussion and
                                      decision analysis through
                                      configurable providers

  Export                              Export the framework and selected
                                      decision information as Markdown

  Privacy                             Provide private accounts,
                                      controlled sharing and data
                                      deletion
  -----------------------------------------------------------------------

The application should not require users to fill in every level. Someone
might have a domain and some Whys without yet having any objectives or
goals. That is a perfectly valid state.

## 8. Technical architecture

The initial implementation should favour simplicity, maintainability and
low operating costs.

### 8.1 Proposed technology

  -----------------------------------------------------------------------
  Component                           Proposed technology
  ----------------------------------- -----------------------------------
  Backend                             Python and Django

  Database                            MariaDB for hosted deployments;
                                      SQLite as a possible local option

  Frontend                            Django templates, HTMX and
                                      Bootstrap

  LLM integration                     Provider-independent adapter using
                                      provider APIs

  Deployment                          Docker Compose

  Source control                      GitHub
  -----------------------------------------------------------------------

This avoids introducing a separate JavaScript application, microservices
or unnecessary infrastructure.

### 8.2 Multi-user and standalone operation

The application should support two deployment patterns:

1.  **Hosted multi-user application:** Multiple people use the same
    installation, with strict separation between their accounts and
    data.
2.  **Standalone installation:** An individual runs the application
    locally, with their data stored on their own device or server.

Both should use the same underlying application and conceptual data
model. Local operation should not depend on a central hosted service.

A local installation should remain useful without an LLM connection. LLM
features should be an enhancement, not a requirement for using the
framework.

### 8.3 Demo system and ephemeral sandbox mode

For publicly accessible evaluation instances, the software should support a dedicated demonstration mode:

1.  **Auto-population of sample data:** On startup or instance reset, the system can automatically populate one or more rich, realistic sample frameworks illustrating varied life situations, cross-domain decisions, and simulated LLM reflection logs.
2.  **No-barrier exploration:** Visitors can explore the interface, examine cross-domain relationships, test decision workflows, and inspect export outputs without needing to register personal accounts or provide external LLM API credentials.
3.  **Periodic scheduled reset:** To prevent data accumulation or inappropriate modifications by public visitors, the application should support an automated periodic refresh mechanism (e.g., a management command executed via systemd timer or cron) that safely purges visitor changes and restores the sample framework baseline.
4.  **Security boundaries:** Demo mode instances must disable administrative account elevation from the web UI and prevent external SSRF or unauthenticated credential exposure.

### 8.4 Initial data model

The initial database model should be deliberately small.

  -----------------------------------------------------------------------
  Model                               Principal fields and relationships
  ----------------------------------- -----------------------------------
  User                                Account and authentication
                                      information

  Framework                           Owner, name and description

  Domain                              Framework, name, description and
                                      display order

  Why                                 Domain, title, description and
                                      display order

  Objective                           Primary domain, title, description,
                                      status

  Goal                                Primary domain, title, description,
                                      status and optional target date

  Objective--Why link                 Connects an objective to one or
                                      more Whys

  Goal--Objective link                Connects a goal to one or more
                                      objectives

  Related domain                      Optional links from objectives and
                                      goals to additional domains

  Decision record                     User, decision description,
                                      analysis and outcome
  -----------------------------------------------------------------------

The model should allow for more than one framework per user, even if
most people initially create only one.

There is no need for a generic relationship engine, a separate
responsibility model or a complicated philosophical taxonomy in the
first release.

## 9. Privacy and security

Privacy is a fundamental product requirement.

The application should:

-   Make all user frameworks private by default.
-   Enforce ownership and access permissions at the server level.
-   Prevent users from accessing other users' records.
-   Use HTTPS for hosted deployments.
-   Store provider API keys securely, encrypted at rest.
-   Avoid advertising and unnecessary tracking.
-   Minimise the information accessible to application administrators.
-   Allow users to export and delete their information.
-   Clearly disclose what information is sent to an external LLM
    provider.
-   Require user consent before sharing framework data with an external
    provider.

The application should not assume that a user's framework is suitable
for public sharing simply because the user has chosen to use an LLM.

## 10. User experience and design principles

The interface should be calm, straightforward and easy to understand.

The user should be able to see their framework without being overwhelmed
by forms, scoring systems or complex diagrams.

Key principles:

-   Organise the main view by domain.
-   Keep Whys, objectives and goals visibly distinct.
-   Make it easy to move between a domain's overall picture and the
    details of individual items.
-   Provide help at the point where it is needed.
-   Avoid requiring users to complete a prescribed sequence.
-   Allow incomplete and evolving frameworks.
-   Make editing and revising information straightforward.
-   Keep LLM suggestions separate from the user's own recorded
    information.

The application should feel like a personal thinking tool, not a
project-management system or a corporate performance dashboard.

## 11. MVP scope

The first release should establish the core framework and demonstrate
that it is useful in everyday decision-making.

### 11.1 Include in MVP

1.  User accounts and private frameworks.
2.  Domain creation and management.
3.  Whys within domains.
4.  Objectives linked to Whys.
5.  Goals linked to objectives.
6.  Optional related-domain links.
7.  Contextual guidance and optional sample content.
8.  A basic cross-domain decision-assessment workflow.
9.  LLM integration through at least one provider.
10. Markdown export with LLM harness instructions.
11. Basic status and review functionality.
12. Local deployment instructions.

### 11.2 Defer until later

-   Automated public demo system with periodic reset timers (specified in §8.3; implementation deferred to a post-MVP phase).
-   Complex visualisations and relationship diagrams.
-   Numerical scoring and weighted-priority calculations.
-   Advanced analytics and reporting.
-   Multiple users collaborating on a shared framework.
-   Extensive historical tracking and version comparisons.
-   Sophisticated workflow automation.
-   A large library of predefined life frameworks.
-   Mobile-native applications.

These features may be useful later, but they should not complicate the
first release.

## 12. Acceptance criteria

The MVP should be considered successful when a user can:

1.  Create a framework without being forced to adopt predefined domains
    or values.
2.  Create several domains and express multiple Whys within each.
3.  Translate those Whys into objectives and goals.
4.  See the relationship between the four levels clearly.
5.  Identify when an objective or goal affects more than one domain.
6.  Enter a proposed opportunity or decision and examine its
    implications across their framework.
7.  See potential conflicts and trade-offs without being given an
    artificial numerical ranking.
8.  Discuss the analysis with an LLM while retaining control over the
    conclusions.
9.  Export their framework as useful Markdown for use with an external
    LLM.
10. Use the application without an LLM connection.
11. Be confident that their information is private and under their
    control.

## 13. Product philosophy

The product should remain faithful to a few principles as it develops:

-   **User-defined:** It does not prescribe what matters in life.
-   **Exploratory:** It helps people discover and clarify their
    thinking.
-   **Practical:** It connects underlying reasons to objectives, goals
    and decisions.
-   **Integrated:** It recognises that decisions in one area of life can
    affect others.
-   **Non-prescriptive:** It exposes tensions and choices rather than
    automatically resolving them.
-   **Transparent:** It distinguishes what the user has said from what
    the software or LLM has inferred.
-   **Private:** Personal priorities and reflections belong to the user.

The central question the product helps a person answer is:

> Given what matters to me, why it matters, and the different
> responsibilities and circumstances of my life, what should I give my
> time, attention and resources to?

## 14. Remaining product decisions

The specification is sufficiently defined to guide an initial design and
implementation. A few decisions can remain open without blocking the
MVP.

  -----------------------------------------------------------------------
  Decision                            Suggested approach
  ----------------------------------- -----------------------------------
  Open-source licence                 Decide before public release. MIT
                                      or Apache 2.0 for permissive reuse;
                                      AGPL-3.0 if hosted modifications
                                      should remain open source.

  Local database                      Support SQLite if practical, while
                                      using MariaDB for the hosted
                                      deployment.

  Priority indicators                 Start with qualitative descriptions
                                      and user-defined non-negotiables,
                                      not numerical scores.

  Review reminders                    Add optional reminders later rather
                                      than making reviews compulsory.

  LLM providers                       Design the adapter for multiple
                                      providers, but implement one first.
  -----------------------------------------------------------------------

**Recommendation:** Keep the first release focused on the core thinking
process, especially the ability to examine a decision across multiple
domains. That is what makes this more than a structured list of personal
goals.

A sensible next step is to turn this specification into a
Django-oriented technical design: database schema, application
structure, principal screens and user journeys. That would make it
concrete enough to start building while preserving the deliberately
simple conceptual model.
