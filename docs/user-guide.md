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
PrioritySuite is private by default. When you sign up, your framework is strictly isolated to your user account. No other user or administrator can view your priorities or decisions.

### 3.2 Workspace & Sample Content
Upon first logging in, you will be taken to your **Workspace**:
- If starting from scratch, click **"+ Add Domain"** to define your first sphere of life.
- If you'd like to explore how the model works, click **"Load Sample Content to Explore"**. This populates realistic starter examples across family, work, and personal development, clearly marked with a **Sample Content** badge.
- You can edit any sample item or remove all samples with a single click at any time.

---

## 4. Cross-Domain Decision Assessments

Real decisions often benefit one area of life while creating strains or opportunity costs in another. The **Decision Assessment** feature provides a structured 7-step exploration:

1. **Proposal / Opportunity:** State what is being considered (e.g. *"A promotion offer involving higher compensation, longer hours, and weekly travel"*).
2. **Affected Domains & Whys:** Select the domains and core convictions engaged by this opportunity.
3. **Supporting Priorities:** Identify existing objectives that this proposal advances.
4. **Competing Tensions / Costs:** Make explicit which objectives or Whys might be compromised, neglected, or stressed.
5. **Benefits, Direct Costs & Opportunity Costs:** Record qualitative reflections.
6. **Alternatives Considered:** Brainstorm alternative paths to achieve the same underlying outcome.
7. **Decision Outcome:** Record your final choice and reasoning for future reflection.

---

## 5. Periodic Review

Click **Periodic Review** in the navigation bar to step back and reflect:
- Filter items by status (**Active**, **Paused**, **Completed**).
- Click **"Mark Reviewed"** on any Why, Objective, or Goal to track when you last reflected on it.

---

## 6. Optional AI Thinking Partner (BYOK)

PrioritySuite can operate completely offline without an LLM. If you choose to enable an AI thinking partner, it operates strictly as a **facilitator and sounding board**, never as an authority on your life.

### 6.1 Supported Providers
Go to **Settings & LLM BYOK** to configure:
- **Ollama (Local / Self-hosted):** Free, private, and runs directly on your machine or local network without sending data over the internet.
  - Default API Base: `http://localhost:11434`
  - Model: e.g. `ollama/llama3.1`
- **OpenRouter (Cloud Router):** Single API key granting access to hundreds of models (Anthropic Claude, OpenAI GPT-4o, Google Gemini, Mistral).
  - API Base: `https://openrouter.ai/api/v1`
  - Model: e.g. `openrouter/anthropic/claude-3.5-sonnet`

### 6.2 Privacy & Epistemic Guardrails
- **Encrypted at rest:** Your API key is encrypted using AES-128-CBC/Fernet encryption.
- **Explicit consent:** No data is sent to an LLM provider until you check the explicit consent checkbox in Settings.
- **Epistemic humility:** The thinking partner prompt strictly enforces that the model must distinguish between what you have *explicitly stated*, what it has *inferred*, and what it is *suggesting*.

---

## 7. Markdown Export

Click **"Export Markdown"** on your Framework or any Decision Assessment to view, copy, or download a `.md` file.

The export includes:
- Embedded facilitator instructions for any external LLM.
- A concise summary of the conceptual framework.
- Your structured Domains, Whys, Objectives, and Goals.
- You can copy and paste this into ChatGPT, Claude, Gemini, or any desktop AI app.

---

## 8. Autumnal Theme (Light / Dark Mode)

Click the **🍂 Theme** button in the top navigation bar at any time to switch between:
- **Autumn Parchment (Light):** Warm cream and parchment tones with terracotta and sage accents.
- **Autumn Woodland (Dark):** Deep woodland charcoal and warm umber tones with copper and amber highlights.
