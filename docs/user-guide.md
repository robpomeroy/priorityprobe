# PrioritySuite User Guide

## 1. What is PrioritySuite?

PrioritySuite is a private, user-led application designed to help you articulate what matters to you and why, translate those reasons into objectives and practical goals, and evaluate real-life opportunities and decisions against your wider framework.

The software helps you examine and apply your priorities without telling you what to value or calculating artificial numerical scores.

---

## 2. The Core Thinking Model

The conceptual structure flows through four distinct levels:

```
Domains ➔ Whys ➔ Objectives ➔ Goals
```

- **Domain:** A broad sphere of life (e.g. *Family & Home*, *Work & Vocation*, *Personal Health & Renewal*). These are relatively stable.
- **Why:** The enduring reason something matters in that domain. Why should anything happen here? Whys may express convictions, commitments, aspirations, or responsibilities. You can optionally designate a Why as **Non-Negotiable**.
- **Objective:** What you would like your Whys to lead to (e.g. *Build financial resilience and a stable home environment*). Reviewed periodically.
- **Goal:** Specific, practical actions, changes, or milestones (e.g. *Establish an emergency buffer of £10,000 over two years*).

---

## 3. Getting Started

### 3.1 Account Creation & Privacy
PrioritySuite is private by default. When you sign up, your framework is strictly isolated to your user account, preventing other regular users from viewing or modifying your priorities or decisions. (System administrators operating the database or backend have server-level access as with any hosted web service).

### 3.2 Workspace & Reordering
Upon first logging in, you will be taken to your **Workspace**:
- If starting from scratch, click **"+ Add Domain"** to define your first sphere of life.
- If you'd like to explore how the model works, click **"Load Sample Content to Explore"**. This populates realistic starter examples across family, work, and personal development, clearly marked with a **Sample Content** badge.
- **Reordering:** Use the **◀ / ▶** buttons in the header of each domain card to reorder your domains, and the **▲ / ▼** buttons on each Why card to adjust the display order of your foundational reasons.
- **Quick Status Changes:** Click the three-dots menu on any Objective or Goal card to change its status (**Active**, **Paused**, **Completed**, **Abandoned**) instantly without leaving the workspace canvas.
- You can edit any sample item or remove all samples with a single click at any time.

---

## 4. Cross-Domain Priorities & Decision Support

### 4.1 Cross-Domain Priority Comparison
Real commitments frequently compete across domains for limited hours, energy, and financial resources. Click **"Compare Priorities"** in the navigation bar to:
- Select two or more Objectives or Goals across different domains.
- Review a side-by-side comparison matrix highlighting affected primary and related domains, underlying Whys (with any **[Non-Negotiable]** markers), and dependent goals.
- Engage structured qualitative prompts (e.g., *"Where do these commitments compete for time, attention, or energy?"*).
- Click **"Save as Decision Assessment"** to convert the compared priorities into a formal decision record, or **"Discuss Tensions with Thinking Partner"** to analyze qualitative trade-offs with your configured LLM.

### 4.2 Cross-Domain Decision Assessments
Real decisions often benefit one area of life while creating strains or opportunity costs in another. The **Decision Assessment** feature provides a structured 7-step exploration:

Real decisions often benefit one area of life while creating strains or opportunity costs in another. The **Decision Assessment** feature provides a structured 7-step exploration:

1. **Proposal / Opportunity:** State what is being considered (e.g. *"A promotion offer involving higher compensation, longer hours, and weekly travel"*).
2. **Affected Domains & Whys:** Select the domains and core convictions engaged by this opportunity.
3. **Supporting Priorities:** Identify existing objectives that this proposal advances.
4. **Competing Tensions / Costs:** Make explicit which objectives or Whys might be compromised, neglected, or stressed.
5. **Benefits, Direct Costs & Opportunity Costs:** Record qualitative reflections.
6. **Alternatives Considered:** Brainstorm alternative paths to achieve the same underlying outcome.
7. **Decision Outcome:** Record your final choice and reasoning for future reflection.

---

## 5. Periodic Review & Cadence Tracking

Click **Periodic Review** in the navigation bar to step back and reflect:
- **Status Filter:** Focus on **Active**, **Paused**, **Completed**, or **Abandoned** items.
- **Cadence & Staleness Filter:** Identify priorities needing attention by filtering for items **Never Reviewed**, or those unreviewed for **>90 days**, **>180 days**, or **>1 year**.
- **Review Actions:** Click **"Mark Reviewed"** on any individual Why, Objective, or Goal, or use the **"Mark All Reviewed"** batch action to update your entire framework at once.
- **Status Management:** Quickly update status directly from review cards.

---

## 6. Optional AI Thinking Partner (BYOK)

PrioritySuite can operate completely offline without an LLM. If you choose to enable an AI thinking partner, it operates strictly as a **facilitator and sounding board**, never as an authority on your life.

### 6.1 Supported Providers & Gateways
Go to **Settings & LLM BYOK** to configure your preferred connection:
- **Ollama (Local / Self-hosted):** Free, private, and runs directly on your machine or local network without sending data over the internet.
  - Default API Base: `http://localhost:11434`
  - Model: e.g. `ollama/llama3.1`
- **OpenRouter (Cloud Router):** Single API key granting access to hundreds of models (Anthropic Claude, OpenAI GPT-4o, Google Gemini, Mistral).
  - API Base: `https://openrouter.ai/api/v1`
  - Model: e.g. `openrouter/anthropic/claude-3.5-sonnet`
- **OpenAI (Direct API):** Direct access with OpenAI API key (e.g. `gpt-4o`, `gpt-4o-mini`).
- **Anthropic Claude (Direct API):** Direct access with Anthropic API key (e.g. `claude-3-5-sonnet-20241022`).
- **Google Gemini (Direct API):** Direct access with Google Gemini API key (e.g. `gemini-2.0-flash`).
- **OpenAI-Compatible Gateway (Custom Endpoint):** Connect to self-hosted proxies and local engines including **LiteLLM Proxy**, **vLLM**, **LM Studio**, **LocalAI**, or **llama.cpp** using standard OpenAI API conventions.
- **Test Connection:** Click **"Test Connection"** on the Settings page to verify your credentials, endpoint reachability, and response latency.

### 6.2 User-Controlled Context & Guided Modes
In the Thinking Partner interface (`/llm/framework/<id>/chat/`):
- **Guided Thinking Modes:** Select from built-in facilitation prompts:
  - *Articulate & Refine Whys:* Clarify deeper enduring reasons vs. surface tasks.
  - *Spot Gaps & Contradictions:* Identify unlinked objectives or competing commitments.
  - *Formulate Objectives & Goals:* Translate reasons into actionable directions.
  - *Periodic Framework Review:* Review stalled or paused items and overall life balance.
- **Context Customization:** Open **"Customize Context Shared with LLM"** to selectively choose which domains and decision records are sent, toggle conversation continuity, and inspect the exact Markdown payload before submitting.
- **Reflection History & Management:** Delete individual reflection records at any time.

### 6.3 Privacy & Epistemic Guardrails
- **Encrypted at rest:** Your API key is encrypted using AES-128-CBC/Fernet encryption.
- **Explicit consent:** No data is sent to an LLM provider until you check the explicit consent checkbox in Settings.
- **Epistemic humility:** The thinking partner prompt strictly enforces that the model must distinguish between what you have *explicitly stated*, what it has *inferred*, and what it is *suggesting*.

---

## 7. Selective Markdown Export Builder

Click **"Export Markdown"** on your Framework to view, copy, or download a `.md` file.

The interactive export builder allows you to:
- Select which **Domains** to include in the bundle.
- Include or exclude specific **Decision Assessments**.
- Toggle the embedded **LLM Facilitator Instructions** header.
- Toggle whether to include recent **Thinking Partner Reflections**.
- Copy the resulting bundle to your clipboard or download as a safe, sanitized `.md` file.

---

## 8. Autumnal Theme (Light / Dark Mode)

Click the **🍂 Theme** button in the top navigation bar at any time to switch between:
- **Autumn Parchment (Light):** Warm cream and parchment tones with terracotta and sage accents.
- **Autumn Woodland (Dark):** Deep woodland charcoal and warm umber tones with copper and amber highlights.
