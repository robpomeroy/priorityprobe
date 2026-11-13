import contextlib
import socket
import threading
import litellm
from django.conf import settings
from typing import List, Dict, Optional, Tuple

_dns_thread_local = threading.local()
_original_getaddrinfo = socket.getaddrinfo

def _coerce_port(port, default_port=0):
    if port is None or port == 0:
        return default_port
    if isinstance(port, int):
        return port
    if isinstance(port, str):
        if port.isdigit():
            return int(port)
        try:
            return socket.getservbyname(port)
        except (OSError, socket.error):
            return default_port
    return default_port

def _thread_scoped_getaddrinfo(host, port, *args, **kwargs):
    pinned = getattr(_dns_thread_local, "pinned_dns", None)
    if pinned and host:
        host_key = host.lower()
        if host_key in pinned:
            safe_ip, target_port = pinned[host_key]
            is_v6 = ":" in safe_ip
            family = socket.AF_INET6 if is_v6 else socket.AF_INET
            resolved_port = _coerce_port(port, target_port)
            sockaddr = (safe_ip, resolved_port, 0, 0) if is_v6 else (safe_ip, resolved_port)
            return [(family, socket.SOCK_STREAM, 6, "", sockaddr)]
    return _original_getaddrinfo(host, port, *args, **kwargs)

socket.getaddrinfo = _thread_scoped_getaddrinfo

@contextlib.contextmanager
def _pinned_dns(target_host: str, target_port: int, safe_ip: str):
    if not hasattr(_dns_thread_local, "pinned_dns") or _dns_thread_local.pinned_dns is None:
        _dns_thread_local.pinned_dns = {}
    host_key = target_host.lower()
    previous = _dns_thread_local.pinned_dns.get(host_key)
    _dns_thread_local.pinned_dns[host_key] = (safe_ip, target_port)
    try:
        yield
    finally:
        if previous is None:
            _dns_thread_local.pinned_dns.pop(host_key, None)
        else:
            _dns_thread_local.pinned_dns[host_key] = previous

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

    pinned_api_base = resolved_api_base
    extra_headers = {}
    dns_pin_target = None

    if resolved_api_base and provider in ("ollama", "custom"):
        import ipaddress
        from urllib.parse import urlparse, urlunparse
        from accounts.forms import is_safe_ollama_endpoint

        parsed = urlparse(resolved_api_base)
        host_str = parsed.hostname or ""
        port = parsed.port

        try:
            addr_infos = socket.getaddrinfo(host_str, port or 80, socket.AF_UNSPEC)
            if not addr_infos:
                return False, f"Could not resolve destination host '{host_str}'."

            allowlist = getattr(settings, "OLLAMA_ALLOWED_HOSTS", None) or []
            normalized_allowlist = {h.strip().lower() for h in allowlist if h.strip()}
            host_explicitly_allowlisted = (host_str.lower() in normalized_allowlist)

            resolved_ips = []
            for family, socktype, proto, canonname, sockaddr in addr_infos:
                ip_str = sockaddr[0]
                if ip_str in ("169.254.169.254", "metadata.google.internal"):
                    return False, f"Outbound connection blocked: destination {ip_str} is private or restricted."
                if not host_explicitly_allowlisted and not is_safe_ollama_endpoint(ip_str):
                    return False, f"Outbound connection blocked: destination {ip_str} is private or restricted."
                resolved_ips.append(ip_str)

            safe_ip = resolved_ips[0]
            safe_ip_formatted = f"[{safe_ip}]" if ":" in safe_ip else safe_ip

            if parsed.scheme == "https":
                pinned_api_base = resolved_api_base
            else:
                pinned_netloc = f"{safe_ip_formatted}:{port}" if port else safe_ip_formatted
                pinned_api_base = urlunparse(parsed._replace(netloc=pinned_netloc))

            if host_str and host_str != safe_ip:
                dns_pin_target = (host_str, port or (443 if parsed.scheme == "https" else 80), safe_ip)
                extra_headers["Host"] = host_str
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

    if pinned_api_base:
        kwargs["api_base"] = pinned_api_base

    if extra_headers:
        kwargs["extra_headers"] = extra_headers

    try:
        if dns_pin_target:
            with _pinned_dns(*dns_pin_target):
                response = litellm.completion(**kwargs)
        else:
            response = litellm.completion(**kwargs)
        content = response.choices[0].message.content
        return True, content
    except Exception as exc:
        return False, f"LLM Connection Error: {str(exc)}"
