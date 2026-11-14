import os
import socket
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import httpx
import litellm
import openai
from django.conf import settings

# Prevent LiteLLM from making outbound network calls to download cost maps on init
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
litellm.telemetry = False
litellm.suppress_debug_info = True

class SSRFSafeTransport(httpx.HTTPTransport):
    """
    HTTP transport that enforces SSRF validation on every destination host/IP
    and disables automatic redirect following at the transport layer.
    """
    def __init__(self, allowlist: Optional[List[str]] = None, **kwargs):
        self.allowlist = {h.strip().lower() for h in (allowlist or []) if h.strip()}
        super().__init__(**kwargs)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        from accounts.forms import is_safe_ollama_endpoint
        host = (request.url.host or "").strip().lower()
        port = request.url.port or (443 if request.url.scheme == "https" else 80)

        if not host:
            raise ValueError("Invalid request: host is empty.")

        if host in ("169.254.169.254", "metadata.google.internal"):
            raise ValueError(f"Outbound connection blocked: destination {host} is private or restricted.")

        # Check explicit hostname allowlist
        if host in self.allowlist or ("localhost" in self.allowlist and host in ("127.0.0.1", "::1", "0:0:0:0:0:0:0:1")):
            return super().handle_request(request)

        # Resolve host to IP addresses (supports dual-stack IPv4/IPv6)
        try:
            addr_infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except Exception as exc:
            raise ValueError(f"Could not resolve destination host '{host}': {exc}")

        for family, socktype, proto, canonname, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            if ip_str in ("169.254.169.254", "metadata.google.internal") or not is_safe_ollama_endpoint(ip_str):
                raise ValueError(f"Outbound connection blocked: destination {ip_str} is private or restricted.")

        return super().handle_request(request)

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

GUIDED_MODES = {
    "general": {
        "title": "General Thinking Partner",
        "description": "Open exploration of priorities, balance, and clarifying questions.",
        "prompt": "Reflect on my overall priorities framework. Ask clarifying questions to help me examine qualitative tensions and balance across domains.",
    },
    "refine_whys": {
        "title": "Articulate & Refine Whys",
        "description": "Distinguish enduring motivations and core convictions from surface goals.",
        "prompt": "Examine the Whys articulated in my framework. Are any phrased merely as practical tasks or surface objectives rather than enduring reasons? What clarifying questions can help me articulate the deeper reason why these areas matter?",
    },
    "spot_gaps": {
        "title": "Spot Gaps & Contradictions",
        "description": "Identify unlinked objectives, overloaded domains, or conflicting priorities.",
        "prompt": "Analyze my framework for potential blind spots: Are there domains without active objectives? Objectives without underlying Whys? Or apparent tensions between commitments across different domains?",
    },
    "formulate_objectives": {
        "title": "Formulate Objectives & Goals",
        "description": "Translate foundational Whys into actionable directions and practical goals.",
        "prompt": "Help me translate my Whys into meaningful, practical objectives and concrete goals without imposing arbitrary deadlines or external metrics.",
    },
    "periodic_review": {
        "title": "Periodic Framework Review",
        "description": "Assess stalled or paused priorities and review overall balance.",
        "prompt": "Guide me through a periodic review of my framework. Highlight items that have been paused or inactive, and help me reflect on whether my current focus aligns with my enduring Whys.",
    },
}

def generate_reflection(
    user_context_markdown: str,
    user_prompt: str,
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    timeout: int = 60,
) -> Tuple[bool, str]:
    """
    Vendor-neutral completion wrapper using LiteLLM.
    Supports Ollama, OpenRouter, OpenAI, Anthropic, Gemini, and custom OpenAI-compatible gateways.
    """
    if provider == "none" or not model_name:
        return False, "LLM integration is currently disabled or unconfigured in your settings."

    # Normalize model prefix for LiteLLM routing
    normalized_model = model_name.strip()
    if provider == "custom" and not normalized_model.startswith("openai/"):
        normalized_model = f"openai/{normalized_model}"
    elif provider == "gemini" and not normalized_model.startswith("gemini/"):
        normalized_model = f"gemini/{normalized_model}"
    elif provider == "anthropic" and not normalized_model.startswith("anthropic/"):
        normalized_model = f"anthropic/{normalized_model}"
    elif provider == "openai" and not normalized_model.startswith("openai/"):
        normalized_model = f"openai/{normalized_model}"

    # Validate api_base to prevent SSRF and DNS rebinding
    resolved_api_base = api_base
    if not resolved_api_base and provider == "ollama":
        resolved_api_base = "http://localhost:11434"

    if resolved_api_base or provider in ("ollama", "custom"):
        from accounts.forms import validate_llm_api_base
        from django.core.exceptions import ValidationError
        try:
            validate_llm_api_base(provider, resolved_api_base or "")
        except ValidationError as e:
            return False, f"Invalid API base URL: {'; '.join(e.messages)}"

    if resolved_api_base and provider in ("ollama", "custom"):
        from accounts.forms import is_safe_ollama_endpoint
        parsed = urlparse(resolved_api_base)
        host_str = (parsed.hostname or "").strip()
        port = parsed.port

        try:
            addr_infos = socket.getaddrinfo(host_str, port or 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if not addr_infos:
                return False, f"Could not resolve destination host '{host_str}'."

            allowlist = getattr(settings, "OLLAMA_ALLOWED_HOSTS", None) or []
            normalized_allowlist = {h.strip().lower() for h in allowlist if h.strip()}
            host_explicitly_allowlisted = (host_str.lower() in normalized_allowlist)

            for family, socktype, proto, canonname, sockaddr in addr_infos:
                ip_str = sockaddr[0]
                if ip_str in ("169.254.169.254", "metadata.google.internal"):
                    return False, f"Outbound connection blocked: destination {ip_str} is private or restricted."
                if not host_explicitly_allowlisted and not is_safe_ollama_endpoint(ip_str):
                    return False, f"Outbound connection blocked: destination {ip_str} is private or restricted."
        except Exception as exc:
            return False, f"Destination safety check failed: {str(exc)}"

    # Format messages: system -> previous conversation history -> current prompt
    messages = [
        {"role": "system", "content": SYSTEM_FACILITATOR_PROMPT},
    ]

    if history:
        for item in history:
            messages.append(item)

    messages.append({
        "role": "user",
        "content": f"Here is my current Priorities Framework context:\n\n{user_context_markdown}\n\nUser Question/Scenario:\n{user_prompt}",
    })

    kwargs = {
        "model": normalized_model,
        "messages": messages,
        "temperature": 0.4,
        "timeout": timeout,
    }

    if api_key:
        kwargs["api_key"] = api_key

    if resolved_api_base:
        kwargs["api_base"] = resolved_api_base

    try:
        if provider in ("ollama", "custom"):
            allowlist = getattr(settings, "OLLAMA_ALLOWED_HOSTS", None) or []
            transport = SSRFSafeTransport(allowlist=allowlist)
            http_client = httpx.Client(transport=transport, follow_redirects=False, timeout=timeout)
            client = openai.OpenAI(
                base_url=resolved_api_base,
                api_key=api_key or "sk-dummy",
                http_client=http_client,
            )
            kwargs["client"] = client

        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content
        return True, content
    except Exception as exc:
        return False, f"LLM Connection Error: {str(exc)}"
