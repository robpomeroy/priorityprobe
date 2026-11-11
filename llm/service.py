import litellm
from django.conf import settings
from typing import List, Dict, Optional, Tuple

SYSTEM_FACILITATOR_PROMPT = """You are a facilitator, sounding board, and analytical assistant for PrioritySuite, a personal priorities and decision-making framework suite.

Core Philosophy:
1. The user defines what matters in their life. You must NEVER prescribe values, morals, or how the user ought to live.
2. Distinguish clearly between:
   - What the user has EXPLICITLY STATED
   - What you have INFERRED or deduced
   - What you are SUGGESTING or proposing as an alternative
   - What remains UNCERTAIN, ambiguous, or unresolved
3. Do not silently convert an inference into an established user priority.
4. When examining decisions, do not calculate artificial numerical scores or weighted rankings. Instead, highlight qualitative tensions, conflicts, and trade-offs across domains, while respecting user-defined non-negotiables.
5. Ask thoughtful, clarifying questions rather than rushing to conclusions.

Structure your reflections into clear headings:
### Stated Priorities
(Ground your reflection in what the user explicitly recorded in their framework.)

### Potential Tensions & Inferences
(Examine how the proposal interacts with competing domains, whys, or objectives. Clearly label inferences: "I infer that...")

### Alternative Approaches & Unresolved Questions
(Constructive alternatives and questions to help the user reflect.)
"""

def generate_reflection(
    user_context_markdown: str,
    user_prompt: str,
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[bool, str]:
    """
    Vendor-neutral completion wrapper using LiteLLM.
    Supports Ollama, OpenRouter, and other providers without vendor-specific code.
    """
    if provider == "none" or not model_name:
        return False, "LLM integration is currently disabled or unconfigured in your settings."

    # Validate api_base to prevent SSRF
    if api_base:
        from accounts.forms import validate_llm_api_base
        from django.core.exceptions import ValidationError
        try:
            validate_llm_api_base(provider, api_base)
        except ValidationError as e:
            return False, f"Invalid API base URL: {'; '.join(e.messages)}"

    # Format messages
    messages = [
        {"role": "system", "content": SYSTEM_FACILITATOR_PROMPT},
        {
            "role": "user",
            "content": f"Here is my current Priorities Framework context:\n\n{user_context_markdown}\n\nUser Question/Scenario:\n{user_prompt}",
        },
    ]

    if history:
        for item in history:
            messages.append(item)

    kwargs = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.4,
    }

    if api_key:
        kwargs["api_key"] = api_key

    if api_base:
        kwargs["api_base"] = api_base

    try:
        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content
        return True, content
    except Exception as exc:
        return False, f"LLM Connection Error: {str(exc)}"
