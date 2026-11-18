import ipaddress
import logging
import os
import socket
from typing import Any
from urllib.parse import urlparse

try:
    import httpx2 as httpx
except ImportError:
    import httpx  # type: ignore[no-redef]

# Prevent LiteLLM from making outbound network calls to download cost maps on init
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm
import openai
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

litellm.telemetry = False
litellm.suppress_debug_info = True


class SSRFSafeTransport(httpx.HTTPTransport):
    """
    HTTP transport that enforces SSRF validation on every destination host/IP
    and disables automatic redirect following at the transport layer.
    """

    def __init__(self, allowlist: list[str] | None = None, **kwargs):
        self.allowlist = {h.strip().lower() for h in (allowlist or []) if h.strip()}
        super().__init__(**kwargs)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        from accounts.forms import CLOUD_METADATA_HOSTS, is_restricted_ip, is_safe_ollama_endpoint

        original_host = (request.url.host or "").strip().lower()
        original_port = request.url.port
        port = original_port or (443 if request.url.scheme == "https" else 80)

        if not original_host:
            raise ValueError("Invalid request: host is empty.")

        if original_host in CLOUD_METADATA_HOSTS:
            raise ValueError(
                f"Outbound connection blocked: destination {original_host} "
                "is private or restricted."
            )

        # Check explicit hostname allowlist
        is_allowlisted = original_host in self.allowlist or (
            "localhost" in self.allowlist
            and original_host in ("127.0.0.1", "::1", "0:0:0:0:0:0:0:1")
        )

        # Resolve host to IP addresses (supports dual-stack IPv4/IPv6)
        try:
            addr_infos = socket.getaddrinfo(
                original_host, port, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
        except (socket.gaierror, OSError, ValueError) as exc:
            raise ValueError(
                f"Could not resolve destination host '{original_host}': {exc}"
            ) from exc

        safe_ips = []
        for family, _socktype, _proto, _canonname, sockaddr in addr_infos:
            ip_str = str(sockaddr[0])
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if is_restricted_ip(ip_obj):
                    raise ValueError(
                        f"Outbound connection blocked: destination {ip_str} "
                        "is private or restricted."
                    )
            except ValueError as val_err:
                if "Outbound connection blocked" in str(val_err):
                    raise
                raise ValueError(
                    f"Outbound connection blocked: destination {ip_str} is invalid or restricted."
                ) from val_err

            if not is_allowlisted and not is_safe_ollama_endpoint(ip_str):
                raise ValueError(
                    f"Outbound connection blocked: destination {ip_str} is private or restricted."
                )
            safe_ips.append((family, ip_str))

        if not safe_ips:
            raise ValueError(f"Could not resolve safe destination IP for '{original_host}'.")

        # In dual-stack environments, prefer IPv4 for localhost to avoid ::1 connection refused
        # when local services (e.g. Ollama) listen only on 127.0.0.1
        safe_ip = safe_ips[0][1]
        for family, ip_str in safe_ips:
            if family == socket.AF_INET:
                safe_ip = ip_str
                break

        # Pin validated IP address on request to eliminate TOCTOU DNS rebinding
        is_default_port = (request.url.scheme == "https" and port == 443) or (
            request.url.scheme == "http" and port == 80
        )
        formatted_host = (
            f"[{original_host}]"
            if ":" in original_host and not original_host.startswith("[")
            else original_host
        )
        host_header_val = (
            formatted_host
            if (not original_port or is_default_port)
            else f"{formatted_host}:{original_port}"
        )
        request.headers["Host"] = host_header_val
        if request.url.scheme == "https":
            request.extensions["sni_hostname"] = original_host
        request.url = request.url.copy_with(host=safe_ip)

        return super().handle_request(request)


SYSTEM_FACILITATOR_PROMPT = """You are a facilitator, sounding board, and analytical assistant for
PrioritySuite, a personal priorities and decision-making framework suite.

Core Philosophy:
1. The user defines what matters in their life. You must NEVER prescribe values, morals, or how
   the user ought to live.
2. Distinguish clearly between:
   - What the user has EXPLICITLY STATED
   - What you have INFERRED or deduced
   - What you are SUGGESTING or proposing as an alternative
   - What remains UNCERTAIN, ambiguous, or unresolved
3. Do not silently convert an inference into an established user priority.
4. When examining decisions, do not calculate artificial numerical scores or weighted rankings.
   Instead, highlight qualitative tensions, conflicts, and trade-offs across domains, while
   respecting user-defined non-negotiables.
5. Ask thoughtful, clarifying questions rather than rushing to conclusions.

Structure your reflections into clear headings:
### Stated Priorities
(Ground your reflection in what the user explicitly recorded in their framework.)

### Potential Tensions & Inferences
(Examine how the proposal interacts with competing domains, whys, or objectives.
Clearly label inferences: "I infer that...")

### Alternative Approaches & Unresolved Questions
(Constructive alternatives and questions to help the user reflect.)
"""

GUIDED_MODES = {
    "general": {
        "title": "General Thinking Partner",
        "description": "Open exploration of priorities, balance, and clarifying questions.",
        "prompt": (
            "Reflect on my overall priorities framework. Ask clarifying questions "
            "to help me examine qualitative tensions and balance across domains."
        ),
    },
    "refine_whys": {
        "title": "Articulate & Refine Whys",
        "description": "Distinguish enduring motivations and core convictions from surface goals.",
        "prompt": (
            "Examine the Whys articulated in my framework. Are any phrased merely as "
            "practical tasks or surface objectives rather than enduring reasons? "
            "What clarifying questions can help me articulate the deeper reason why "
            "these areas matter?"
        ),
    },
    "spot_gaps": {
        "title": "Spot Gaps & Contradictions",
        "description": (
            "Identify unlinked objectives, overloaded domains, or conflicting priorities."
        ),
        "prompt": (
            "Analyze my framework for potential blind spots: Are there domains without "
            "active objectives? Objectives without underlying Whys? Or apparent tensions "
            "between commitments across different domains?"
        ),
    },
    "formulate_objectives": {
        "title": "Formulate Objectives & Goals",
        "description": (
            "Translate foundational Whys into actionable directions and practical goals."
        ),
        "prompt": (
            "Help me translate my Whys into meaningful, practical objectives and concrete "
            "goals without imposing arbitrary deadlines or external metrics."
        ),
    },
    "periodic_review": {
        "title": "Periodic Framework Review",
        "description": "Assess stalled or paused priorities and review overall balance.",
        "prompt": (
            "Guide me through a periodic review of my framework. Highlight items that "
            "have been paused or inactive, and help me reflect on whether my current "
            "focus aligns with my enduring Whys."
        ),
    },
}


def generate_reflection(
    user_context_markdown: str,
    user_prompt: str,
    provider: str,
    model_name: str,
    api_key: str | None = None,
    api_base: str | None = None,
    history: list[dict[str, str]] | None = None,
    timeout: int = 30,
) -> tuple[bool, str]:
    """
    Vendor-neutral completion wrapper using LiteLLM.
    Supports Ollama, OpenRouter, OpenAI, Anthropic, Gemini, and custom OpenAI-compatible gateways.
    """
    if provider == "none" or not model_name:
        return False, "LLM integration is currently disabled or unconfigured in your settings."

    valid_providers = {"ollama", "openrouter", "openai", "anthropic", "gemini", "custom"}
    if provider not in valid_providers:
        return False, f"Unsupported LLM provider: {provider}"

    # BYOK enforcement: Cloud providers require a user API key
    if provider in {"openrouter", "openai", "anthropic", "gemini"} and not (api_key or "").strip():
        return False, "An API key is required for the selected LLM provider."

    # Normalize model prefix for LiteLLM routing
    normalized_model = model_name.strip()
    if provider == "custom" and not normalized_model.startswith("openai/"):
        normalized_model = f"openai/{normalized_model}"
    elif provider == "ollama":
        normalized_model = normalized_model.removeprefix("ollama/")
        if not normalized_model.startswith("openai/"):
            normalized_model = f"openai/{normalized_model}"
    elif provider == "openrouter":
        if not normalized_model.startswith("openrouter/"):
            normalized_model = f"openrouter/{normalized_model}"
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
    elif not resolved_api_base and provider == "openrouter":
        resolved_api_base = "https://openrouter.ai/api/v1"

    if provider == "ollama" and resolved_api_base:
        stripped_base = resolved_api_base.rstrip("/")
        if not stripped_base.endswith("/v1"):
            resolved_api_base = f"{stripped_base}/v1"

    if resolved_api_base or provider in ("ollama", "custom"):
        from accounts.forms import validate_llm_api_base

        try:
            validate_llm_api_base(provider, resolved_api_base or "", api_key=api_key)
        except ValidationError as e:
            return False, f"Invalid API base URL: {'; '.join(e.messages)}"

    # Format messages: system -> previous conversation history -> current prompt
    messages = [
        {"role": "system", "content": SYSTEM_FACILITATOR_PROMPT},
    ]

    if history:
        messages.extend(history)

    messages.append(
        {
            "role": "user",
            "content": (
                f"Here is my current Priorities Framework context:\n\n"
                f"{user_context_markdown}\n\n"
                f"User Question/Scenario:\n{user_prompt}"
            ),
        }
    )

    kwargs: dict[str, Any] = {
        "model": normalized_model,
        "messages": messages,
        "temperature": 0.4,
        "timeout": timeout,
        "num_retries": 0,
    }

    if api_key:
        kwargs["api_key"] = api_key

    if resolved_api_base:
        kwargs["api_base"] = resolved_api_base

    http_client = None
    try:
        if provider in ("ollama", "custom"):
            allowlist = getattr(settings, "OLLAMA_ALLOWED_HOSTS", None) or []
            transport = SSRFSafeTransport(allowlist=allowlist)
            http_client = httpx.Client(
                transport=transport, follow_redirects=False, timeout=timeout
            )
            kwargs["client"] = openai.OpenAI(
                base_url=resolved_api_base,
                api_key=api_key or ("sk-dummy" if provider == "custom" else "ollama"),
                http_client=http_client,
                max_retries=0,
            )

        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content
        return True, content
    except Exception as exc:  # noqa: BLE001
        err_msg = str(exc)
        if "Outbound connection blocked:" in err_msg:
            idx = err_msg.index("Outbound connection blocked:")
            return False, err_msg[idx:]
        if isinstance(exc, (ValueError, ValidationError)) and err_msg.startswith(
            ("Invalid API base URL:", "Disallowed")
        ):
            return False, err_msg

        # Redact credentials if echoed in exception
        if api_key and api_key in err_msg:
            err_msg = err_msg.replace(api_key, "[REDACTED]")
        if resolved_api_base:
            try:
                parsed = urlparse(resolved_api_base)
                if parsed.password and parsed.password in err_msg:
                    err_msg = err_msg.replace(parsed.password, "[REDACTED]")
                if parsed.username and parsed.username in err_msg:
                    err_msg = err_msg.replace(parsed.username, "[REDACTED]")
            except ValueError:
                pass

        logger.warning("LLM generation error (%s/%s): %s", provider, normalized_model, err_msg)
        lower_err = err_msg.lower()
        if "timeout" in lower_err:
            sanitized = (
                "The LLM provider request timed out. Please try again or check provider status."
            )
        elif any(
            k in lower_err
            for k in ("unauthorized", "authentication", "api_key", "401", "forbidden")
        ):
            sanitized = (
                "Authentication failed with the LLM provider. "
                "Please check your API key and permissions."
            )
        elif "rate limit" in lower_err or "429" in lower_err:
            sanitized = "Rate limit exceeded with the LLM provider. Please wait and try again."
        else:
            sanitized = (
                "The LLM endpoint could not be reached or returned an error. "
                "Check settings and credentials."
            )
        return False, sanitized
    finally:
        if http_client is not None:
            http_client.close()
