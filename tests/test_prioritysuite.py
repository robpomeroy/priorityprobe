import os
from typing import Any, cast

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User

from accounts.crypto import decrypt_value, encrypt_value
from accounts.models import UserLLMConfig
from decisions.models import DecisionRecord, DecisionStatus, LLMReflectionLog
from exports.services import generate_framework_markdown
from frameworks.models import Domain, Framework, Goal, Objective, StatusChoices, Why
from frameworks.services import remove_sample_frameworks, seed_sample_framework


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="password123"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="otheruser", email="other@example.com", password="password123"
    )


@pytest.fixture
def framework(user):
    return Framework.objects.create(owner=user, name="Personal Priorities")


@pytest.fixture
def domain(framework):
    return Domain.objects.create(framework=framework, name="Work & Vocation", display_order=1)


@pytest.fixture
def why(domain):
    return Why.objects.create(domain=domain, title="To do honest work", is_non_negotiable=True)


@pytest.fixture
def objective(domain, why):
    obj = Objective.objects.create(
        primary_domain=domain, title="Maintain craft excellence", status=StatusChoices.ACTIVE
    )
    obj.whys.add(why)
    return obj


@pytest.fixture
def goal(domain, objective):
    g = Goal.objects.create(primary_domain=domain, title="Ship MVP", status=StatusChoices.ACTIVE)
    g.objectives.add(objective)
    return g


# --- 1. Crypto & Accounts Tests ---


def test_crypto_roundtrip():
    raw = "sk-openrouter-secret-key-12345"
    enc = encrypt_value(raw)
    assert enc != raw
    dec = decrypt_value(enc)
    assert dec == raw
    assert decrypt_value("") == ""
    assert encrypt_value("") == ""


def test_user_llm_config_encryption(user):
    config = UserLLMConfig.objects.create(
        user=user, provider="openrouter", model_name="openrouter/anthropic/claude-3.5-sonnet"
    )
    config.api_key = "secret-key-test"
    config.save()

    assert config.api_key == "secret-key-test"
    assert config._encrypted_api_key != "secret-key-test"
    assert str(config).startswith("LLM Config for testuser")


def test_user_registration_and_login(db, client):
    response = client.post(
        "/accounts/register/",
        {
            "username": "newperson",
            "email": "new@example.com",
            "password": "strongpassword123",
            "password_confirm": "strongpassword123",
        },
    )
    assert response.status_code == 302
    assert User.objects.filter(username="newperson").exists()


def test_user_registration_mismatch(db, client):
    response = client.post(
        "/accounts/register/",
        {
            "username": "newperson2",
            "email": "new2@example.com",
            "password": "strongpassword123",
            "password_confirm": "wrong",
        },
    )
    assert response.status_code == 200
    assert not User.objects.filter(username="newperson2").exists()


def test_user_settings_update(client, user):
    client.force_login(user)
    response = client.post(
        "/accounts/settings/",
        {
            "provider": "openrouter",
            "model_name": "openrouter/anthropic/claude-3.5-sonnet",
            "api_base": "https://openrouter.ai/api/v1",
            "raw_api_key": "new-secret-api-key",
            "consent_given": True,
            "theme_preference": "dark",
        },
    )
    assert response.status_code == 302
    config = user.llm_config
    assert config.provider == "openrouter"
    assert config.api_key == "new-secret-api-key"
    assert config.consent_given is True
    assert config.theme_preference == "dark"


def test_user_delete_account(client, user, framework):
    client.force_login(user)
    response = client.post("/accounts/delete-account/")
    assert response.status_code == 302
    assert not User.objects.filter(id=user.id).exists()
    assert not Framework.objects.filter(id=framework.id).exists()


# --- 2. Frameworks & Seeder Tests ---


def test_framework_str_and_relationships(framework, domain, why, objective, goal):
    assert str(framework) == f"Personal Priorities ({framework.owner.username})"
    assert str(domain) == "Work & Vocation"
    assert str(why) == "To do honest work"
    assert str(objective) == "Maintain craft excellence"
    assert str(goal) == "Ship MVP"
    assert objective.whys.first() == why
    assert goal.objectives.first() == objective


def test_sample_seeder_and_removal(user):
    sample_fw = seed_sample_framework(user)
    assert sample_fw.is_sample is True
    assert sample_fw.domains.count() >= 3
    assert Why.objects.filter(domain__framework=sample_fw).count() >= 4

    # Remove samples
    deleted_count = remove_sample_frameworks(user)
    assert deleted_count == 1
    assert not Framework.objects.filter(id=sample_fw.id).exists()


def test_workspace_view(client, user, framework, domain):
    client.force_login(user)
    response = client.get(f"/frameworks/framework/{framework.id}/")
    assert response.status_code == 200
    assert "Work &amp; Vocation" in response.content.decode()


def test_crud_domain(client, user, framework):
    client.force_login(user)
    # Create
    resp = client.post(
        f"/frameworks/framework/{framework.id}/domain/create/",
        {
            "name": "Personal Growth",
            "description": "Continuous learning and stewardship",
            "display_order": 2,
        },
    )
    assert resp.status_code == 302
    d = Domain.objects.get(name="Personal Growth")
    # Edit
    resp = client.post(
        f"/frameworks/domain/{d.id}/edit/",
        {
            "name": "Personal Development",
            "description": "Updated",
            "display_order": 3,
        },
    )
    assert resp.status_code == 302
    d.refresh_from_db()
    assert d.name == "Personal Development"
    # Delete
    resp = client.post(f"/frameworks/domain/{d.id}/delete/")
    assert resp.status_code == 302
    assert not Domain.objects.filter(id=d.id).exists()


def test_crud_why(client, user, domain):
    client.force_login(user)
    # Create Why
    resp = client.post(
        f"/frameworks/domain/{domain.id}/why/create/",
        {
            "title": "To provide for my dependents",
            "description": "Financial stewardship",
            "is_non_negotiable": True,
            "display_order": 1,
        },
    )
    assert resp.status_code == 302
    w = Why.objects.get(title="To provide for my dependents")
    assert w.is_non_negotiable is True
    # Edit Why
    resp = client.post(
        f"/frameworks/why/{w.id}/edit/",
        {
            "title": "To support my family well",
            "description": "Updated",
            "is_non_negotiable": False,
            "display_order": 2,
        },
    )
    assert resp.status_code == 302
    w.refresh_from_db()
    assert w.title == "To support my family well"
    assert w.is_non_negotiable is False
    # Delete
    resp = client.post(f"/frameworks/why/{w.id}/delete/")
    assert resp.status_code == 302
    assert not Why.objects.filter(id=w.id).exists()


def test_crud_objective_and_goal(client, user, framework, domain, why):
    client.force_login(user)
    # Create Objective
    resp = client.post(
        f"/frameworks/framework/{framework.id}/objective/create/",
        {
            "primary_domain": domain.id,
            "title": "Build emergency fund",
            "description": "Resilience buffer",
            "whys": [why.id],
            "status": "ACTIVE",
        },
    )
    assert resp.status_code == 302
    obj = Objective.objects.get(title="Build emergency fund")

    # Create Goal
    resp = client.post(
        f"/frameworks/framework/{framework.id}/goal/create/",
        {
            "primary_domain": domain.id,
            "title": "Save £10k",
            "description": "Over 2 years",
            "objectives": [obj.id],
            "status": "ACTIVE",
        },
    )
    assert resp.status_code == 302
    g = Goal.objects.get(title="Save £10k")

    # Delete Objective & Goal
    client.post(f"/frameworks/goal/{g.id}/delete/")
    client.post(f"/frameworks/objective/{obj.id}/delete/")
    assert not Goal.objects.filter(id=g.id).exists()
    assert not Objective.objects.filter(id=obj.id).exists()


def test_review_and_mark_reviewed(client, user, why, objective, goal):
    client.force_login(user)
    resp = client.get("/frameworks/review/")
    assert resp.status_code == 200

    resp = client.post(f"/frameworks/review/mark/why/{why.id}/", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    why.refresh_from_db()
    assert why.last_reviewed_at is not None

    # Mark objective reviewed: verify update_fields preserves concurrent status changes
    objective.status = "PAUSED"
    objective.save()
    resp_obj = client.post(f"/frameworks/review/mark/objective/{objective.id}/")
    assert resp_obj.status_code == 302
    objective.refresh_from_db()
    assert objective.last_reviewed_at is not None
    assert objective.status == "PAUSED"


def test_status_update_with_update_fields(client, user, objective, goal):
    client.force_login(user)
    import datetime

    test_date = datetime.date(2025, 1, 1)
    objective.last_reviewed_at = test_date
    objective.save()

    # Post status change for objective: update_fields ensures last_reviewed_at is preserved
    resp = client.post(f"/frameworks/objective/{objective.id}/status/", {"status": "PAUSED"})
    assert resp.status_code == 302
    objective.refresh_from_db()
    assert objective.status == "PAUSED"
    assert objective.last_reviewed_at == test_date

    goal.last_reviewed_at = test_date
    goal.save()
    resp_g = client.post(f"/frameworks/goal/{goal.id}/status/", {"status": "COMPLETED"})
    assert resp_g.status_code == 302
    goal.refresh_from_db()
    assert goal.status == "COMPLETED"
    assert goal.last_reviewed_at == test_date


# --- 3. Decisions Tests ---


def test_decisions_workflow(client, user, framework, domain, why, objective):
    client.force_login(user)
    # List View
    resp_list = client.get("/decisions/")
    assert resp_list.status_code == 200

    # Create Decision (GET and invalid POST)
    resp_create_get = client.get("/decisions/create/")
    assert resp_create_get.status_code == 200

    resp_create_inv = client.post("/decisions/create/", {"title": ""})
    assert resp_create_inv.status_code == 200
    assert "title" in resp_create_inv.context["form"].errors

    # Create Decision
    resp = client.post(
        "/decisions/create/",
        {
            "title": "Promotion Offer",
            "proposal_description": "Step into VP Engineering role with 30% more travel",
            "affected_domains": [domain.id],
            "relevant_whys": [why.id],
            "supporting_objectives": [objective.id],
            "conflicting_objectives": [],
            "benefits_and_costs": "More money, less family time",
            "status": "EXPLORING",
        },
    )
    assert resp.status_code == 302
    dec = DecisionRecord.objects.get(title="Promotion Offer")
    assert dec.affected_domains.first() == domain

    # Detail View
    resp = client.get(f"/decisions/{dec.id}/")
    assert resp.status_code == 200
    assert "Promotion Offer" in resp.content.decode()

    # Edit Decision (GET and valid POST)
    resp_edit_get = client.get(f"/decisions/{dec.id}/edit/")
    assert resp_edit_get.status_code == 200

    resp = client.post(
        f"/decisions/{dec.id}/edit/",
        {
            "title": "Promotion Offer (Revised)",
            "proposal_description": "Negotiated remote options",
            "status": "DECIDED",
            "decision_outcome": "Accepted with remote boundary",
        },
    )
    assert resp.status_code == 302
    dec.refresh_from_db()
    assert dec.status == DecisionStatus.DECIDED

    # Delete Decision (GET confirm and POST delete)
    resp_del_get = client.get(f"/decisions/{dec.id}/delete/")
    assert resp_del_get.status_code == 200

    resp = client.post(f"/decisions/{dec.id}/delete/")
    assert resp.status_code == 302
    assert not DecisionRecord.objects.filter(id=dec.id).exists()


# --- 4. Exports & LLM Adapter Tests ---


def test_markdown_export(client, user, framework, domain, why, objective, goal):
    client.force_login(user)
    md = generate_framework_markdown(framework, include_instructions=True)
    assert "# Framework: Personal Priorities" in md
    assert "## Domain: Work & Vocation" in md
    assert "Facilitator Instructions for LLM" in md
    assert "# PrioritySuite — Personal Priorities" in md

    # Web View & Download
    resp = client.get(f"/exports/framework/{framework.id}/")
    assert resp.status_code == 200

    resp = client.get(f"/exports/framework/{framework.id}/?download=1")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/markdown")


@patch("litellm.completion")
def test_llm_service_reflection_mocked(mock_completion, user, framework):
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        "### Stated Priorities\nYou value honest work.\n\n"
        "### Potential Tensions & Inferences\nI infer promotion creates time strain."
    )
    mock_response.choices = [mock_choice]
    mock_completion.return_value = mock_response

    from llm.service import generate_reflection

    success, reflection = generate_reflection(
        user_context_markdown="# Context",
        user_prompt="Examine this choice",
        provider="openrouter",
        model_name="openrouter/anthropic/claude-3.5-sonnet",
        api_key="test-key",
    )
    assert success is True
    assert "### Stated Priorities" in reflection
    assert mock_completion.called


def test_llm_service_disabled():
    from llm.service import generate_reflection

    success, msg = generate_reflection(
        user_context_markdown="# Context",
        user_prompt="Hello",
        provider="none",
        model_name="",
    )
    assert success is False
    assert "disabled" in msg


@patch("litellm.completion")
def test_chat_view_reflection(mock_completion, client, user, framework, settings):
    settings.OLLAMA_ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Insightful reflection"
    mock_response.choices = [mock_choice]
    mock_completion.return_value = mock_response

    # Give consent
    config, _ = UserLLMConfig.objects.get_or_create(user=user)
    config.consent_given = True
    config.provider = "ollama"
    config.model_name = "ollama/llama3.1"
    config.save()

    client.force_login(user)
    resp = client.post(
        f"/llm/framework/{framework.id}/chat/",
        {
            "prompt": "Evaluate my framework",
        },
    )
    assert resp.status_code == 302
    assert LLMReflectionLog.objects.filter(framework=framework).exists()


# --- 5. Strict User Isolation Security Tests ---


def test_cross_user_isolation(client, user, other_user, framework, domain):
    client.force_login(other_user)
    # Attempting to access or delete another user's domain/framework must return 404
    resp = client.get(f"/frameworks/framework/{framework.id}/")
    assert resp.status_code == 404

    resp = client.post(f"/frameworks/domain/{domain.id}/delete/")
    assert resp.status_code == 404
    assert Domain.objects.filter(id=domain.id).exists()


# Additional Coverage Tests to exceed 85%


def test_crypto_custom_key():
    from accounts.crypto import get_cipher

    with patch("accounts.crypto.settings") as mock_settings:
        mock_settings.SECRET_KEY = "test"
        mock_settings.ENCRYPTION_KEY = "custom-key-of-any-arbitrary-length"
        cipher = get_cipher()
        assert cipher is not None


def test_crypto_legacy_sha256_backward_compatibility(settings):
    import base64
    import hashlib

    from cryptography.fernet import Fernet

    from accounts.crypto import decrypt_value

    # Case 1: Derived from SECRET_KEY when ENCRYPTION_KEY is empty
    settings.ENCRYPTION_KEY = ""
    settings.SECRET_KEY = "test-secret-key-12345"
    raw_key = settings.SECRET_KEY
    legacy_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest())
    legacy_cipher = Fernet(legacy_key)
    secret_text = "sk-legacy-test-api-key-12345"
    legacy_ciphertext = legacy_cipher.encrypt(secret_text.encode("utf-8")).decode("utf-8")

    # MultiFernet must seamlessly decrypt ciphertext created with legacy SHA-256 key
    decrypted = decrypt_value(legacy_ciphertext)
    assert decrypted == secret_text

    # Case 2: Direct Fernet ENCRYPTION_KEY with legacy derived fallback
    direct_key = Fernet.generate_key().decode("utf-8")
    settings.ENCRYPTION_KEY = direct_key
    legacy_direct_key = base64.urlsafe_b64encode(
        hashlib.sha256(direct_key.encode("utf-8")).digest()
    )
    legacy_direct_cipher = Fernet(legacy_direct_key)
    legacy_direct_ciphertext = (
        legacy_direct_cipher.encrypt(secret_text.encode("utf-8")).decode("utf-8")
    )
    decrypted_direct = decrypt_value(legacy_direct_ciphertext)
    assert decrypted_direct == secret_text


def test_ipv6_loopback_not_restricted():
    import ipaddress

    from accounts.forms import is_restricted_ip

    # RFC 4291 defines ::1 as loopback, but ip.is_reserved is True for 0000::/8.
    # Our loopback exemption must ensure is_restricted_ip returns False.
    assert is_restricted_ip(ipaddress.IPv6Address("::1")) is False
    assert is_restricted_ip(ipaddress.IPv4Address("127.0.0.1")) is False
    # Link-local / metadata IPs are restricted; public unicast is not
    assert is_restricted_ip(ipaddress.IPv4Address("169.254.169.254")) is True
    assert is_restricted_ip(ipaddress.IPv4Address("8.8.8.8")) is False


def test_crypto_decrypt_failure():
    assert decrypt_value("invalid-gibberish-string") == ""


def test_decision_views_edge_cases(client, user, framework, domain, why, objective):
    client.force_login(user)
    # Decision reflection when consent not given
    cfg, _ = UserLLMConfig.objects.get_or_create(user=user)
    cfg.consent_given = False
    cfg.save()

    dec = DecisionRecord.objects.create(
        framework=framework,
        title="Test Dec",
        proposal_description="Test desc",
    )
    dec.affected_domains.add(domain)
    dec.relevant_whys.add(why)
    dec.supporting_objectives.add(objective)
    dec.conflicting_objectives.add(objective)
    dec.benefits_and_costs = "Benefits notes"
    dec.alternatives_considered = "Alt notes"
    dec.unresolved_questions = "Q notes"
    dec.decision_outcome = "Outcome notes"
    dec.save()

    # Reflect view redirects with warning when no consent
    resp = client.post(f"/decisions/{dec.id}/reflect/")
    assert resp.status_code == 302

    # Export decision download
    resp = client.get(f"/exports/decision/{dec.id}/?download=1")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/markdown")

    # Export decision html preview
    resp = client.get(f"/exports/decision/{dec.id}/")
    assert resp.status_code == 200

    # Test reflection execution on decision with mocked litellm
    cfg.consent_given = True
    cfg.provider = "openrouter"
    cfg.model_name = "openrouter/anthropic/claude-3.5-sonnet"
    cfg.api_base = "https://openrouter.ai/api/v1"
    cfg.api_key = "sk-or-test-key"
    cfg.save()

    with patch("litellm.completion") as mock_comp:
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="### Stated Priorities\nGood"))]
        mock_comp.return_value = mock_resp

        resp = client.post(f"/decisions/{dec.id}/reflect/", {"prompt": "Analyze tensions"})
        assert resp.status_code == 302
        assert dec.reflections.count() >= 1


def test_framework_views_modals_and_gets(client, user, framework, domain, why, objective, goal):
    client.force_login(user)

    # GET forms
    assert client.get(f"/frameworks/framework/{framework.id}/domain/create/").status_code == 200
    assert client.get(f"/frameworks/domain/{domain.id}/edit/").status_code == 200
    assert client.get(f"/frameworks/domain/{domain.id}/delete/").status_code == 200
    assert client.get(f"/frameworks/domain/{domain.id}/why/create/").status_code == 200
    assert client.get(f"/frameworks/why/{why.id}/edit/").status_code == 200
    assert client.get(f"/frameworks/why/{why.id}/delete/").status_code == 200
    assert client.get(f"/frameworks/framework/{framework.id}/objective/create/").status_code == 200
    assert client.get(f"/frameworks/objective/{objective.id}/edit/").status_code == 200
    assert client.get(f"/frameworks/objective/{objective.id}/delete/").status_code == 200
    assert client.get(f"/frameworks/framework/{framework.id}/goal/create/").status_code == 200
    assert client.get(f"/frameworks/goal/{goal.id}/edit/").status_code == 200
    assert client.get(f"/frameworks/goal/{goal.id}/delete/").status_code == 200
    assert client.get("/decisions/create/").status_code == 200

    # Mark reviewed for objective and goal
    resp = client.post(
        f"/frameworks/review/mark/objective/{objective.id}/", HTTP_HX_REQUEST="true"
    )
    assert resp.status_code == 200
    resp = client.post(f"/frameworks/review/mark/goal/{goal.id}/", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200

    # Filter review by status
    assert client.get("/frameworks/review/?status=ACTIVE").status_code == 200


def test_chat_view_empty_and_no_consent(client, user, framework):
    client.force_login(user)
    cfg, _ = UserLLMConfig.objects.get_or_create(user=user)
    cfg.consent_given = False
    cfg.save()

    # GET chat
    assert client.get(f"/llm/framework/{framework.id}/chat/").status_code == 200

    # POST without consent
    resp = client.post(f"/llm/framework/{framework.id}/chat/", {"prompt": "Hello"})
    assert resp.status_code == 302

    # POST with consent but empty prompt
    cfg.consent_given = True
    cfg.save()
    resp = client.post(f"/llm/framework/{framework.id}/chat/", {"prompt": ""})
    assert resp.status_code == 302


# --- Tests for Copilot Review Fixes ---


def test_secret_key_production_error():
    import importlib
    import os
    import sys
    from unittest.mock import patch

    from django.conf import settings

    old_debug = getattr(settings, "DEBUG", True)
    # Ensure config.settings raises ValueError when imported with empty key and DEBUG=False
    with patch.dict(os.environ, {"DJANGO_SECRET_KEY": "", "DEBUG": "False"}):
        if "config.settings" in sys.modules:
            del sys.modules["config.settings"]
        with pytest.raises(ValueError, match="DJANGO_SECRET_KEY must be set in production"):
            importlib.import_module("config.settings")

    # Restore settings module for subsequent tests
    if "config.settings" in sys.modules:
        del sys.modules["config.settings"]
    importlib.import_module("config.settings")
    settings._setup()
    settings.DEBUG = old_debug


def test_api_base_ssrf_validation(client, user):
    client.force_login(user)
    # Metadata IP blocked
    resp = client.post(
        "/accounts/settings/",
        {
            "provider": "openrouter",
            "model_name": "openrouter/anthropic/claude-3.5-sonnet",
            "api_base": "http://169.254.169.254/latest/meta-data/",
            "consent_given": True,
            "theme_preference": "auto",
        },
    )
    assert resp.status_code == 200
    assert "cloud metadata endpoints is prohibited" in resp.content.decode()

    # OpenRouter non-https blocked
    resp = client.post(
        "/accounts/settings/",
        {
            "provider": "openrouter",
            "model_name": "openrouter/anthropic/claude-3.5-sonnet",
            "api_base": "http://openrouter.ai/api/v1",
            "consent_given": True,
            "theme_preference": "auto",
        },
    )
    assert resp.status_code == 200
    assert "OpenRouter connections must use HTTPS" in resp.content.decode()


def test_admin_queryset_filtering(user, other_user, framework, domain, why, objective, goal):
    from django.contrib.admin.sites import AdminSite

    from accounts.admin import UserLLMConfigAdmin
    from accounts.models import UserLLMConfig
    from decisions.admin import DecisionRecordAdmin
    from frameworks.admin import (
        DomainAdmin,
        FrameworkAdmin,
        GoalAdmin,
        ObjectiveAdmin,
        WhyAdmin,
    )

    site = AdminSite()
    f_admin = FrameworkAdmin(Framework, site)
    d_admin = DomainAdmin(Domain, site)
    w_admin = WhyAdmin(Why, site)
    o_admin = ObjectiveAdmin(Objective, site)
    g_admin = GoalAdmin(Goal, site)
    dec_admin = DecisionRecordAdmin(DecisionRecord, site)
    llm_admin = UserLLMConfigAdmin(UserLLMConfig, site)

    # Regular staff user (not superuser)
    other_user.is_staff = True
    other_user.save()

    request = MagicMock()
    request.user = other_user
    assert f_admin.get_queryset(request).count() == 0
    assert d_admin.get_queryset(request).count() == 0
    assert w_admin.get_queryset(request).count() == 0
    assert o_admin.get_queryset(request).count() == 0
    assert g_admin.get_queryset(request).count() == 0
    assert dec_admin.get_queryset(request).count() == 0
    assert llm_admin.get_queryset(request).count() == 0

    # User's own staff request
    user_req = MagicMock()
    user_req.user = user
    user_req.user.is_superuser = False
    assert w_admin.get_queryset(user_req).count() >= 1
    assert o_admin.get_queryset(user_req).count() >= 1
    assert g_admin.get_queryset(user_req).count() >= 1

    # Permissions on UserOwnedAdmin (Why, Objective, Goal) and UserLLMConfigAdmin
    cfg, _ = UserLLMConfig.objects.get_or_create(user=user)
    with patch.object(User, "has_perm", return_value=True):
        assert w_admin.has_change_permission(user_req, why) is True
        assert w_admin.has_delete_permission(user_req, why) is True
        assert w_admin.has_change_permission(request, why) is False
        assert w_admin.has_delete_permission(request, why) is False

        assert o_admin.has_change_permission(user_req, objective) is True
        assert o_admin.has_delete_permission(user_req, objective) is True
        assert o_admin.has_change_permission(request, objective) is False
        assert o_admin.has_delete_permission(request, objective) is False

        assert g_admin.has_change_permission(user_req, goal) is True
        assert g_admin.has_delete_permission(user_req, goal) is True
        assert g_admin.has_change_permission(request, goal) is False
        assert g_admin.has_delete_permission(request, goal) is False

        assert llm_admin.has_change_permission(user_req, cfg) is True
        assert llm_admin.has_delete_permission(user_req, cfg) is True
        assert llm_admin.has_change_permission(request, cfg) is False
        assert llm_admin.has_delete_permission(request, cfg) is False

        u_field = llm_admin.formfield_for_foreignkey(
            UserLLMConfig._meta.get_field("user"), user_req
        )
        assert u_field.queryset.count() == 1
        llm_admin.save_model(user_req, cfg, None, False)
        assert cfg.user == user
        assert llm_admin.has_add_permission(user_req) is False

    # Foreign key and M2M formfield scoping for regular staff
    fw_field = d_admin.formfield_for_foreignkey(Domain._meta.get_field("framework"), request)
    assert fw_field.queryset.filter(owner=other_user).count() == 0
    assert fw_field.queryset.filter(owner=user).count() == 0

    w_field = w_admin.formfield_for_foreignkey(Why._meta.get_field("domain"), user_req)
    assert w_field.queryset.filter(framework__owner=user).count() >= 1

    o_field = o_admin.formfield_for_foreignkey(
        Objective._meta.get_field("primary_domain"), user_req
    )
    assert o_field.queryset.filter(framework__owner=user).count() >= 1

    o_whys = o_admin.formfield_for_manytomany(Objective._meta.get_field("whys"), user_req)
    assert o_whys.queryset.filter(domain__framework__owner=user).count() >= 1

    o_domains = o_admin.formfield_for_manytomany(
        Objective._meta.get_field("related_domains"), user_req
    )
    assert o_domains.queryset.filter(framework__owner=user).count() >= 1

    g_field = g_admin.formfield_for_foreignkey(Goal._meta.get_field("primary_domain"), user_req)
    assert g_field.queryset.filter(framework__owner=user).count() >= 1

    g_objs = g_admin.formfield_for_manytomany(Goal._meta.get_field("objectives"), user_req)
    assert g_objs.queryset.filter(primary_domain__framework__owner=user).count() >= 1

    g_domains = g_admin.formfield_for_manytomany(Goal._meta.get_field("related_domains"), user_req)
    assert g_domains.queryset.filter(framework__owner=user).count() >= 1

    # FrameworkAdmin save_model and formfield_for_foreignkey
    new_fw = Framework(name="New Staff FW")
    f_admin.save_model(user_req, new_fw, None, False)
    assert new_fw.owner == user

    fw_owner_field = f_admin.formfield_for_foreignkey(Framework._meta.get_field("owner"), user_req)
    assert fw_owner_field.queryset.count() == 1
    assert fw_owner_field.queryset.first() == user

    dec_fw_field = dec_admin.formfield_for_foreignkey(
        DecisionRecord._meta.get_field("framework"), request
    )
    assert dec_fw_field.queryset.filter(owner=other_user).count() == 0

    # Create UserLLMConfig for user
    UserLLMConfig.objects.get_or_create(user=user)

    # Superuser sees all
    request.user.is_superuser = True
    assert f_admin.get_queryset(request).count() >= 1
    assert d_admin.get_queryset(request).count() >= 1
    assert w_admin.get_queryset(request).count() >= 1
    assert o_admin.get_queryset(request).count() >= 1
    assert g_admin.get_queryset(request).count() >= 1
    assert llm_admin.get_queryset(request).count() >= 1


def test_decision_empty_prompt_uses_default(client, user, framework):
    client.force_login(user)
    cfg, _ = UserLLMConfig.objects.get_or_create(user=user)
    cfg.consent_given = True
    cfg.provider = "ollama"
    cfg.model_name = "ollama/llama3.1"
    cfg.save()

    dec = DecisionRecord.objects.create(
        framework=framework,
        title="Default Prompt Test",
        proposal_description="Test description",
    )

    with patch("decisions.views.generate_reflection") as mock_gen:
        mock_gen.return_value = (True, "Analysis response")
        resp = client.post(f"/decisions/{dec.id}/reflect/", {"prompt": "   "})
        assert resp.status_code == 302
        assert mock_gen.called
        # Verify the prompt sent was not blank
        called_prompt = mock_gen.call_args[1]["user_prompt"]
        assert "Analyze the cross-domain tensions" in called_prompt


def test_registration_password_policy(client, db):
    # Common password rejected
    resp = client.post(
        "/accounts/register/",
        {
            "username": "weakuser1",
            "email": "weak1@example.com",
            "password": "password",
            "password_confirm": "password",
        },
    )
    assert resp.status_code == 200
    assert not User.objects.filter(username="weakuser1").exists()

    # Short password rejected
    resp = client.post(
        "/accounts/register/",
        {
            "username": "weakuser2",
            "email": "weak2@example.com",
            "password": "abc",
            "password_confirm": "abc",
        },
    )
    assert resp.status_code == 200
    assert not User.objects.filter(username="weakuser2").exists()


def test_decision_export_instructions_and_filename_sanitization(client, user, framework):
    client.force_login(user)
    dec = DecisionRecord.objects.create(
        framework=framework,
        title='Unsafe\r\nTitle "With" Slashes/And/Quotes',
        proposal_description="Test proposal",
    )
    # Decision export content contains facilitator instructions
    resp = client.get(f"/exports/decision/{dec.id}/")
    assert resp.status_code == 200
    assert "Facilitator Instructions for LLM" in resp.context["markdown_content"]

    # Download header does not contain newlines or double quotes from the title
    resp_dl = client.get(f"/exports/decision/{dec.id}/?download=1")
    assert resp_dl.status_code == 200
    cd = resp_dl["Content-Disposition"]
    assert "\r" not in cd and "\n" not in cd
    assert 'filename="decision_unsafe-title-with-slashesandquotes.md"' in cd


def test_user_llm_admin_add_and_ownership_enforcement(user, other_user):
    from django.contrib.admin.sites import AdminSite

    from accounts.admin import UserLLMConfigAdmin

    site = AdminSite()
    llm_admin = UserLLMConfigAdmin(UserLLMConfig, site)

    other_user.is_staff = True
    other_user.save()

    request = MagicMock()
    request.user = other_user

    # other_user has no config yet -> has_add_permission is True
    assert llm_admin.has_add_permission(request) is True

    # User field foreignkey is scoped to other_user only
    user_field = llm_admin.formfield_for_foreignkey(UserLLMConfig._meta.get_field("user"), request)
    assert user_field.queryset.count() == 1
    assert user_field.queryset.first() == other_user

    # When saved, non-superuser cannot set user to another user
    obj = UserLLMConfig(user=user, provider="ollama")
    llm_admin.save_model(request, obj, form=MagicMock(), change=False)
    assert obj.user == other_user
    obj.save()

    # Once other_user has a config, has_add_permission becomes False (OneToOne)
    assert llm_admin.has_add_permission(request) is False


# --- 13. Phase 2 Enhancements Tests ---


def test_domain_and_why_reordering(client, user, other_user, framework, domain):
    from frameworks.models import Domain, Why

    domain2 = Domain.objects.create(framework=framework, name="Second Domain", display_order=2)
    client.force_login(user)

    # Move domain 1 down
    resp = client.post(f"/frameworks/domain/{domain.id}/move/down/")
    assert resp.status_code == 302
    domain.refresh_from_db()
    domain2.refresh_from_db()
    assert domain.display_order == 2
    assert domain2.display_order == 1

    # Move domain 1 down again (boundary test - already at bottom)
    client.post(f"/frameworks/domain/{domain.id}/move/down/")
    domain.refresh_from_db()
    assert domain.display_order == 2

    # Move domain 1 back up
    client.post(f"/frameworks/domain/{domain.id}/move/up/")
    domain.refresh_from_db()
    domain2.refresh_from_db()
    assert domain.display_order == 1
    assert domain2.display_order == 2

    # Boundary test up (already at top)
    client.post(f"/frameworks/domain/{domain.id}/move/up/")
    domain.refresh_from_db()
    assert domain.display_order == 1

    # Cross-user isolation on domain move
    client.force_login(other_user)
    resp_cross = client.post(f"/frameworks/domain/{domain.id}/move/down/")
    assert resp_cross.status_code == 404

    # Why reordering
    client.force_login(user)
    why1 = Why.objects.create(domain=domain, title="Why 1", display_order=1)
    why2 = Why.objects.create(domain=domain, title="Why 2", display_order=2)

    resp_why = client.post(f"/frameworks/why/{why1.id}/move/down/")
    assert resp_why.status_code == 302
    why1.refresh_from_db()
    why2.refresh_from_db()
    assert why1.display_order == 2
    assert why2.display_order == 1

    client.post(f"/frameworks/why/{why1.id}/move/up/")
    why1.refresh_from_db()
    assert why1.display_order == 1

    # Cross-user isolation on why move
    client.force_login(other_user)
    assert client.post(f"/frameworks/why/{why1.id}/move/down/").status_code == 404

    # Both domains starting with default order 0: moving up does not produce negative display_order
    client.force_login(user)
    d_zero_a = Domain.objects.create(framework=framework, name="Zero A", display_order=0)
    d_zero_b = Domain.objects.create(framework=framework, name="Zero B", display_order=0)
    client.post(f"/frameworks/domain/{d_zero_b.id}/move/up/")
    d_zero_a.refresh_from_db()
    d_zero_b.refresh_from_db()
    assert d_zero_a.display_order >= 0
    assert d_zero_b.display_order >= 0
    assert d_zero_b.display_order < d_zero_a.display_order


def test_objective_and_goal_status_updates(client, user, other_user, objective, goal):
    client.force_login(user)

    # Update objective status
    resp = client.post(
        f"/frameworks/objective/{objective.id}/status/",
        {"status": StatusChoices.PAUSED, "next": "/frameworks/workspace/"},
    )
    assert resp.status_code == 302
    objective.refresh_from_db()
    assert objective.status == StatusChoices.PAUSED

    # Invalid status is ignored
    client.post(f"/frameworks/objective/{objective.id}/status/", {"status": "INVALID_STATUS"})
    objective.refresh_from_db()
    assert objective.status == StatusChoices.PAUSED

    # Cross-user isolation on objective status
    client.force_login(other_user)
    resp_cross = client.post(
        f"/frameworks/objective/{objective.id}/status/", {"status": StatusChoices.ACTIVE}
    )
    assert resp_cross.status_code == 404

    # Goal status update
    client.force_login(user)
    resp_goal = client.post(
        f"/frameworks/goal/{goal.id}/status/", {"status": StatusChoices.COMPLETED}
    )
    assert resp_goal.status_code == 302
    goal.refresh_from_db()
    assert goal.status == StatusChoices.COMPLETED

    # Cross-user isolation on goal status
    client.force_login(other_user)
    assert (
        client.post(
            f"/frameworks/goal/{goal.id}/status/", {"status": StatusChoices.ACTIVE}
        ).status_code
        == 404
    )

    # Open redirect protection: external target is rejected
    client.force_login(user)
    resp_open = client.post(
        f"/frameworks/objective/{objective.id}/status/",
        {"status": StatusChoices.PAUSED, "next": "https://evil.com/phish"},
    )
    assert resp_open.status_code == 302
    assert "evil.com" not in resp_open.url


def test_review_cadence_and_mark_all(client, user, framework, objective, goal):
    from datetime import timedelta

    from django.utils import timezone

    client.force_login(user)

    # Set initial review dates
    objective.last_reviewed_at = (timezone.now() - timedelta(days=120)).date()
    objective.save()
    goal.last_reviewed_at = None
    goal.save()

    # Review page filtering
    resp_never = client.get(f"/frameworks/review/{framework.id}/?age=never")
    assert resp_never.status_code == 200
    assert goal in resp_never.context["goals"]
    assert objective not in resp_never.context["objectives"]

    resp_90 = client.get(f"/frameworks/review/{framework.id}/?age=90")
    assert resp_90.status_code == 200
    assert objective in resp_90.context["objectives"]

    resp_365 = client.get(f"/frameworks/review/{framework.id}/?age=365")
    assert resp_365.status_code == 200
    assert objective not in resp_365.context["objectives"]

    # Mark all reviewed
    resp_mark = client.post(f"/frameworks/review/{framework.id}/mark-all/")
    assert resp_mark.status_code == 302
    objective.refresh_from_db()
    goal.refresh_from_db()
    assert objective.last_reviewed_at == timezone.now().date()
    assert goal.last_reviewed_at == timezone.now().date()


def test_priority_comparison_view(client, user, framework, domain, objective, goal):
    from frameworks.models import Domain, Goal, Objective, Why

    client.force_login(user)

    domain2 = Domain.objects.create(framework=framework, name="Health", display_order=2)
    why2 = Why.objects.create(domain=domain2, title="Longevity & vitality", is_non_negotiable=True)
    obj2 = Objective.objects.create(
        primary_domain=domain2, title="Consistent rest", status=StatusChoices.ACTIVE
    )
    obj2.whys.add(why2)

    # GET comparison view (objectives)
    resp = client.get(
        f"/decisions/compare/{framework.id}/?type=objectives&selected={objective.id}&selected={obj2.id}"
    )
    assert resp.status_code == 200
    assert resp.context["compare_type"] == "objectives"
    assert objective in resp.context["items"]
    assert obj2 in resp.context["items"]

    # GET comparison view (goals)
    goal2 = Goal.objects.create(
        primary_domain=domain2, title="Sleep 8 hours", status=StatusChoices.ACTIVE
    )
    resp_goals = client.get(
        f"/decisions/compare/{framework.id}/?type=goals&selected={goal.id}&selected={goal2.id}"
    )
    assert resp_goals.status_code == 200
    assert resp_goals.context["compare_type"] == "goals"
    assert goal in resp_goals.context["items"]
    assert goal2 in resp_goals.context["items"]

    # POST action=convert_to_decision
    resp_convert = client.post(
        f"/decisions/compare/{framework.id}/",
        {
            "action": "convert_to_decision",
            "type": "objectives",
            "selected": [str(objective.id), str(obj2.id)],
        },
    )
    assert resp_convert.status_code == 302
    assert DecisionRecord.objects.filter(
        framework=framework, title__startswith="Priority Comparison"
    ).exists()

    # POST action=reflect without consent redirects to settings
    resp_no_consent = client.post(
        f"/decisions/compare/{framework.id}/",
        {
            "action": "reflect",
            "type": "objectives",
            "selected": [str(objective.id), str(obj2.id)],
        },
    )
    assert resp_no_consent.status_code == 302
    assert resp_no_consent.url == "/accounts/settings/"

    # Grant consent and test reflection
    config, _ = UserLLMConfig.objects.get_or_create(user=user)
    config.consent_given = True
    config.provider = "ollama"
    config.model_name = "llama3.1"
    config.save()

    with patch(
        "decisions.views.generate_reflection", return_value=(True, "Comparison reflection from AI")
    ):
        resp_reflect = client.post(
            f"/decisions/compare/{framework.id}/",
            {
                "action": "reflect",
                "type": "objectives",
                "selected": [str(objective.id), str(obj2.id)],
                "prompt": "Evaluate trade-offs between craft and rest.",
            },
        )
        assert resp_reflect.status_code == 302
        assert LLMReflectionLog.objects.filter(
            framework=framework, llm_response="Comparison reflection from AI"
        ).exists()

        # Another comparison (different selected IDs) does NOT consume this reflection
        resp_other = client.get(
            f"/decisions/compare/{framework.id}/?type=objectives&selected={objective.id}"
        )
        assert resp_other.status_code == 200
        assert resp_other.context.get("comparison_reflection") is None

        # The matching comparison consumes the reflection
        resp_matching = client.get(
            f"/decisions/compare/{framework.id}/?type=objectives&selected={objective.id}&selected={obj2.id}"
        )
        assert resp_matching.status_code == 200
        assert resp_matching.context["comparison_reflection"] == "Comparison reflection from AI"

        # Subsequent visit to matching comparison no longer has the reflection
        resp_consumed = client.get(
            f"/decisions/compare/{framework.id}/?type=objectives&selected={objective.id}&selected={obj2.id}"
        )
        assert resp_consumed.context.get("comparison_reflection") is None

    # POST action=convert_to_decision with type=goals in request body (without query param)
    resp_convert_goal = client.post(
        f"/decisions/compare/{framework.id}/",
        {
            "action": "convert_to_decision",
            "type": "goals",
            "selected": [str(goal.id), str(goal2.id)],
        },
    )
    assert resp_convert_goal.status_code == 302
    assert DecisionRecord.objects.filter(
        framework=framework, supporting_objectives=objective
    ).exists()

    # POST action=reflect with type=goals, parent objectives with whys, and target_date
    import datetime

    goal.target_date = datetime.date(2026, 12, 31)
    goal.save()
    with patch(
        "decisions.views.generate_reflection", return_value=(True, "Goals comparison reflection")
    ):
        resp_reflect_goal = client.post(
            f"/decisions/compare/{framework.id}/",
            {
                "action": "reflect",
                "type": "goals",
                "selected": [str(goal.id), str(goal2.id)],
            },
        )
        assert resp_reflect_goal.status_code == 302
        assert LLMReflectionLog.objects.filter(
            framework=framework, llm_response="Goals comparison reflection"
        ).exists()

    # POST action=reflect when reflection generation fails displays error message
    with patch(
        "decisions.views.generate_reflection", return_value=(False, "Provider rate limit reached")
    ):
        resp_reflect_fail = client.post(
            f"/decisions/compare/{framework.id}/",
            {
                "action": "reflect",
                "type": "objectives",
                "selected": [str(objective.id), str(obj2.id)],
            },
        )
        assert resp_reflect_fail.status_code == 200
        assert "Provider rate limit reached" in resp_reflect_fail.content.decode()


def test_llm_test_connection_endpoint(client, user):
    client.force_login(user)

    # 1. No consent -> 302 redirect to settings
    resp_no_consent = client.post("/accounts/settings/test-llm/")
    assert resp_no_consent.status_code == 302
    assert resp_no_consent.url == "/accounts/settings/"

    # 2. GET request redirects to settings
    assert client.get("/accounts/settings/test-llm/").status_code == 302

    # Set consent and LLM config
    config, _ = UserLLMConfig.objects.get_or_create(user=user)
    config.consent_given = True
    config.provider = "ollama"
    config.model_name = "llama3:latest"
    config.api_base = "http://localhost:11434"
    config.save()

    # 3. Successful test
    with patch(
        "llm.service.generate_reflection",
        return_value=(True, "PrioritySuite thinking partner connection verified."),
    ):
        resp_ok = client.post("/accounts/settings/test-llm/")
        assert resp_ok.status_code == 302
        assert resp_ok.url == "/accounts/settings/"

    # 4. Connection error test and log credential sanitization
    with (
        patch(
            "llm.service.generate_reflection",
            return_value=(False, "Connection refused with key sk-secret-leak and user:secretpass"),
        ),
        patch("accounts.views.logger.warning") as mock_log_warn,
    ):
        resp_err = client.post(
            "/accounts/settings/test-llm/",
            {
                "provider": "openrouter",
                "model_name": "openrouter/anthropic/claude-3.5-sonnet",
                "api_base": "https://user:secretpass@openrouter.ai/api/v1",
                "raw_api_key": "sk-secret-leak",
                "consent_given": "on",
            },
        )
        assert resp_err.status_code == 302
        assert resp_err.url == "/accounts/settings/"
        assert mock_log_warn.called
        log_args = mock_log_warn.call_args[0]
        logged_base = log_args[4]
        logged_resp = log_args[5]
        assert "secretpass" not in logged_base
        assert "user" not in logged_base
        assert "sk-secret-leak" not in logged_resp
        assert "secretpass" not in logged_resp

    # 5. Testing unsaved form POST values (e.g. changing provider/key in form before clicking Test)
    with patch(
        "llm.service.generate_reflection", return_value=(True, "Verified unsaved settings")
    ) as mock_test_gen:
        resp_unsaved = client.post(
            "/accounts/settings/test-llm/",
            {
                "provider": "openrouter",
                "model_name": "openrouter/anthropic/claude-3.5-sonnet",
                "api_base": "https://openrouter.ai/api/v1",
                "consent_given": "on",
                "raw_api_key": "sk-new-key",
            },
        )
        assert resp_unsaved.status_code == 302
        assert mock_test_gen.called
        assert mock_test_gen.call_args[1]["provider"] == "openrouter"
        assert mock_test_gen.call_args[1]["api_key"] == "sk-new-key"

    # 6. Reject unknown / invalid provider in POST
    resp_invalid_prov = client.post(
        "/accounts/settings/test-llm/",
        {
            "provider": "malicious_unsupported_provider",
            "model_name": "test-model",
            "consent_given": "on",
        },
    )
    assert resp_invalid_prov.status_code == 302
    assert resp_invalid_prov.url == "/accounts/settings/"

    # 7. Do not leak stored key when changing providers without a new key
    config.provider = "openai"
    config.api_key = "sk-secret-openai-key"
    config.save()

    with patch("llm.service.generate_reflection", return_value=(True, "OK")) as mock_test_gen2:
        client.post(
            "/accounts/settings/test-llm/",
            {
                "provider": "anthropic",
                "model_name": "claude-3-haiku",
                "consent_given": "on",
                "raw_api_key": "",
            },
        )
        assert mock_test_gen2.called
        assert mock_test_gen2.call_args[1]["api_key"] == ""

    # Settings save clears previous provider's key when provider changes without a new key
    with patch("accounts.forms.is_safe_ollama_endpoint", return_value=True):
        client.post(
            "/accounts/settings/",
            {
                "provider": "custom",
                "model_name": "custom-model",
                "api_base": "https://custom-gateway.example.com/v1",
                "consent_given": "on",
                "theme_preference": "auto",
                "raw_api_key": "",
            },
        )
    config.refresh_from_db()
    assert config.provider == "custom"
    assert config.api_key == ""

    # Switching to cloud provider without key fails validation
    resp_anthropic = client.post(
        "/accounts/settings/",
        {
            "provider": "anthropic",
            "model_name": "claude-3-haiku",
            "api_base": "",
            "consent_given": "on",
            "theme_preference": "auto",
            "raw_api_key": "",
        },
    )
    assert resp_anthropic.status_code == 200
    assert "An API key is required" in resp_anthropic.content.decode()


def test_selective_markdown_export_builder(client, user, framework, domain, objective, goal):
    from frameworks.models import Domain

    domain2 = Domain.objects.create(framework=framework, name="Finance", display_order=2)
    dec = DecisionRecord.objects.create(
        framework=framework,
        title="Selective Export Decision",
        proposal_description="Test selective export",
    )
    LLMReflectionLog.objects.create(
        framework=framework,
        user_prompt="Test prompt",
        context_snapshot="Test snapshot",
        llm_response="Test reflection response",
        provider_used="mock-model",
    )

    client.force_login(user)

    # Selective export: only domain 1, no decisions, no facilitator instructions, no reflections
    resp = client.get(
        f"/exports/framework/{framework.id}/?download=0&domains={domain.id}&decisions=none&instructions=0&reflections=0"
    )
    assert resp.status_code == 200
    content = resp.context["markdown_content"]
    assert "Work & Vocation" in content
    assert "Finance" not in content
    assert "Selective Export Decision" not in content
    assert "Facilitator Instructions for LLM" not in content
    assert "Test reflection response" not in content

    # Selective export with all options enabled
    resp_all = client.get(
        f"/exports/framework/{framework.id}/?download=0&domains={domain.id}&domains={domain2.id}&decisions={dec.id}&instructions=1&reflections=1"
    )
    assert resp_all.status_code == 200
    content_all = resp_all.context["markdown_content"]
    assert "Work & Vocation" in content_all
    assert "Finance" in content_all
    assert "Selective Export Decision" in content_all
    assert "Facilitator Instructions for LLM" in content_all
    assert "Test reflection response" in content_all

    # Download parameter produces text/markdown attachment
    resp_dl = client.get(f"/exports/framework/{framework.id}/?download=1")
    assert resp_dl.status_code == 200
    assert "text/markdown" in resp_dl["Content-Type"]
    assert "attachment" in resp_dl["Content-Disposition"]

    # Explicit empty domain filter (domains query param present but empty)
    resp_empty_domains = client.get(f"/exports/framework/{framework.id}/?domains=")
    assert resp_empty_domains.status_code == 200
    assert "Work & Vocation" not in resp_empty_domains.context["markdown_content"]
    assert "Finance" not in resp_empty_domains.context["markdown_content"]
    assert resp_empty_domains.context["selected_domain_ids"] == []


def test_llm_chat_context_and_history(client, user, framework, domain, objective):
    config, _ = UserLLMConfig.objects.get_or_create(user=user)
    config.consent_given = True
    config.provider = "ollama"
    config.model_name = "llama3:latest"
    config.save()

    client.force_login(user)

    # Initial reflection log
    LLMReflectionLog.objects.create(
        framework=framework,
        user_prompt="Prior message",
        context_snapshot="Prior context",
        llm_response="Prior AI answer",
        provider_used="llama3:latest",
    )

    with patch(
        "llm.views.generate_reflection", return_value=(True, "Guided advice on tradeoffs")
    ) as mock_gen:
        resp = client.post(
            f"/llm/framework/{framework.id}/chat/",
            {
                "prompt": "How do I choose between these? Focus on trade-offs.",
                "selected_domains": [str(domain.id)],
                "include_history": "1",
            },
        )
        assert resp.status_code == 302
        assert mock_gen.called
        history_passed = mock_gen.call_args[1]["history"]
        assert len(history_passed) == 2
        assert history_passed[0]["content"] == "Prior message"
        assert "Prior context" not in history_passed[0]["content"]

        # Reflection log was created
        assert LLMReflectionLog.objects.filter(
            framework=framework, llm_response="Guided advice on tradeoffs"
        ).exists()

    # All domains unchecked (context filter active with 0 domains selected)
    with patch(
        "llm.views.generate_reflection", return_value=(True, "Response without domains")
    ) as mock_no_dom:
        resp_no_dom = client.post(
            f"/llm/framework/{framework.id}/chat/",
            {
                "prompt": "Evaluate general principles",
                "context_filter_active": "1",
            },
        )
        assert resp_no_dom.status_code == 302
        context_passed = mock_no_dom.call_args[1]["user_context_markdown"]
        assert "## Domain: Work & Vocation" not in context_passed

    # GET chat view displays reflections and guided modes
    resp_get = client.get(f"/llm/framework/{framework.id}/chat/")
    assert resp_get.status_code == 200
    assert "guided_modes" in resp_get.context
    assert resp_get.context["reflections"].count() >= 1


def test_llm_reflection_deletion(client, user, other_user, framework):
    reflection = LLMReflectionLog.objects.create(
        framework=framework,
        user_prompt="Delete me",
        context_snapshot="Snapshot",
        llm_response="Will be deleted",
        provider_used="test",
    )

    # Other user cannot delete
    client.force_login(other_user)
    resp_cross = client.post(f"/llm/reflection/{reflection.id}/delete/")
    assert resp_cross.status_code == 404
    assert LLMReflectionLog.objects.filter(id=reflection.id).exists()

    # Owner can delete
    client.force_login(user)
    resp = client.post(f"/llm/reflection/{reflection.id}/delete/")
    assert resp.status_code == 302
    assert not LLMReflectionLog.objects.filter(id=reflection.id).exists()

    # GET request returns 403 Forbidden
    ref2 = LLMReflectionLog.objects.create(
        framework=framework,
        user_prompt="Keep me",
        context_snapshot="Snapshot",
        llm_response="Keep",
        provider_used="test",
    )
    assert client.get(f"/llm/reflection/{ref2.id}/delete/").status_code == 403


def test_llm_api_base_validation():
    from django.core.exceptions import ValidationError

    from accounts.forms import validate_llm_api_base

    # Allowed providers with valid endpoints
    assert (
        validate_llm_api_base("openai", "https://api.openai.com/v1") == "https://api.openai.com/v1"
    )
    assert (
        validate_llm_api_base("anthropic", "https://api.anthropic.com/v1")
        == "https://api.anthropic.com/v1"
    )
    assert (
        validate_llm_api_base("gemini", "https://generativelanguage.googleapis.com")
        == "https://generativelanguage.googleapis.com"
    )
    assert (
        validate_llm_api_base("openrouter", "https://openrouter.ai/api/v1")
        == "https://openrouter.ai/api/v1"
    )
    assert validate_llm_api_base("none", "http://any-endpoint.com") == "http://any-endpoint.com"

    # In production without allowlist, empty ollama endpoint is rejected
    with pytest.raises(ValidationError, match="Ollama in production requires an explicit"):
        validate_llm_api_base("ollama", "")

    # When localhost is explicitly allowlisted
    from django.conf import settings

    with patch.object(settings, "OLLAMA_ALLOWED_HOSTS", ["localhost"]):
        assert validate_llm_api_base("ollama", "") == ""

    # Invalid scheme (HTTP when HTTPS required)
    with pytest.raises(ValidationError, match="HTTPS"):
        validate_llm_api_base("openai", "http://api.openai.com/v1")
    with pytest.raises(ValidationError, match="HTTPS"):
        validate_llm_api_base("anthropic", "http://api.anthropic.com/v1")
    with pytest.raises(ValidationError, match="HTTPS"):
        validate_llm_api_base("gemini", "http://generativelanguage.googleapis.com")
    with pytest.raises(ValidationError, match="HTTPS"):
        validate_llm_api_base("openrouter", "http://openrouter.ai/api/v1")

    # Invalid hostnames for strict cloud providers
    with pytest.raises(ValidationError, match=r"OpenAI API Base must point to api\.openai\.com"):
        validate_llm_api_base("openai", "https://evil-openai.com/v1")
    with pytest.raises(
        ValidationError, match=r"Anthropic API Base must point to api\.anthropic\.com"
    ):
        validate_llm_api_base("anthropic", "https://evil-anthropic.com/v1")
    with pytest.raises(ValidationError, match="Google Gemini API Base must point to"):
        validate_llm_api_base("gemini", "https://evil-gemini.com/v1")
    with pytest.raises(ValidationError, match=r"OpenRouter API Base must point to openrouter\.ai"):
        validate_llm_api_base("openrouter", "https://evil-openrouter.ai/v1")

    # Cloud metadata prohibition
    with pytest.raises(ValidationError, match="cloud metadata endpoints is prohibited"):
        validate_llm_api_base("ollama", "http://169.254.169.254/v1")
    with pytest.raises(ValidationError, match="cloud metadata endpoints is prohibited"):
        validate_llm_api_base("custom", "http://metadata.google.internal/computeMetadata")

    # Scheme validation
    with pytest.raises(ValidationError, match="must use http or https"):
        validate_llm_api_base("custom", "ftp://example.com/v1")

    # Custom provider requires non-empty explicit API base URL
    with pytest.raises(ValidationError, match="Custom provider requires an explicit API Base URL"):
        validate_llm_api_base("custom", "")

    # Remote Ollama endpoint with an API key requires HTTPS
    with patch("accounts.forms.is_safe_ollama_endpoint", return_value=True):
        with pytest.raises(
            ValidationError,
            match="Ollama remote API base URL must use HTTPS when an API key is configured",
        ):
            validate_llm_api_base(
                "ollama", "http://remote-ollama.example.com:11434/v1", api_key="ollama-secret-key"
            )
        # Local Ollama with an API key is permitted over HTTP
        assert (
            validate_llm_api_base("ollama", "http://localhost:11434/v1", api_key="local-key")
            == "http://localhost:11434/v1"
        )
        assert (
            validate_llm_api_base("ollama", "http://127.0.0.1:11434/v1", api_key="local-key")
            == "http://127.0.0.1:11434/v1"
        )
        # Remote Ollama with HTTPS and API key is permitted
        assert (
            validate_llm_api_base(
                "ollama", "https://remote-ollama.example.com:11434/v1", api_key="ollama-secret-key"
            )
            == "https://remote-ollama.example.com:11434/v1"
        )


def test_coverage_boosters(user, other_user, framework, domain, why, objective):
    from django.contrib.admin.sites import AdminSite

    from accounts.forms import is_safe_ollama_endpoint
    from decisions.admin import DecisionRecordAdmin, LLMReflectionLogAdmin
    from decisions.models import DecisionRecord, LLMReflectionLog
    from llm.service import generate_reflection

    # 1. Endpoint safety checks
    assert is_safe_ollama_endpoint("10.0.0.1") is False
    assert is_safe_ollama_endpoint("192.168.1.1") is False
    assert is_safe_ollama_endpoint("169.254.1.1") is False
    assert is_safe_ollama_endpoint("100.64.0.1") is False
    assert is_safe_ollama_endpoint("100.127.255.254") is False
    assert is_safe_ollama_endpoint("0.0.0.0") is False
    assert is_safe_ollama_endpoint("::ffff:127.0.0.1") is False
    assert is_safe_ollama_endpoint("::ffff:10.0.0.1") is False
    assert is_safe_ollama_endpoint("invalid.host.that.does.not.exist") is False

    import socket

    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 0, 0, 0))],
    ):
        assert is_safe_ollama_endpoint("malicious-ipv6.internal") is False

    # 2. String representations
    dec = DecisionRecord.objects.create(
        framework=framework, title="Str Test", proposal_description="Desc"
    )
    assert "Str Test" in str(dec)
    ref = LLMReflectionLog.objects.create(
        framework=framework,
        user_prompt="P",
        context_snapshot="C",
        llm_response="R",
        provider_used="test",
    )
    assert "Reflection" in str(ref)

    # 3. Model normalization, history ordering, and error branches
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "OK"
    mock_resp.choices = [mock_choice]

    with (
        patch("litellm.completion", return_value=mock_resp) as mock_litellm,
        patch("accounts.forms.is_safe_ollama_endpoint", return_value=True),
    ):
        assert (
            generate_reflection(
                "ctx", "prompt", "custom", "my-vllm", api_base="http://localhost:8000"
            )[0]
            is True
        )
        assert (
            generate_reflection(
                "ctx", "prompt", "gemini", "gemini-1.5-flash", api_key="test-key"
            )[0]
            is True
        )
        assert (
            generate_reflection(
                "ctx", "prompt", "anthropic", "claude-3-haiku", api_key="test-key"
            )[0]
            is True
        )
        assert (
            generate_reflection(
                "ctx", "prompt", "openai", "gpt-4o", api_key="test-key"
            )[0]
            is True
        )

        # Custom model containing slashes (e.g. meta-llama/Llama-3-8B-Instruct) gets openai/ prefix
        generate_reflection(
            "ctx",
            "prompt",
            "custom",
            "meta-llama/Llama-3-8B-Instruct",
            api_base="http://localhost:8000",
        )
        assert mock_litellm.call_args[1]["model"] == "openai/meta-llama/Llama-3-8B-Instruct"

        # Verify history is placed before current prompt
        generate_reflection(
            "ctx",
            "latest query",
            "ollama",
            "llama3",
            history=[{"role": "user", "content": "prior turn"}],
        )
        sent_messages = mock_litellm.call_args[1]["messages"]
        assert sent_messages[0]["role"] == "system"
        assert sent_messages[1]["content"] == "prior turn"
        assert "latest query" in sent_messages[2]["content"]

    # DNS rebinding protection: destination resolving to private IP is blocked
    with (
        patch(
            "accounts.forms.validate_llm_api_base", return_value="https://rebind.attacker.com/v1"
        ),
        patch(
            "socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))],
        ),
        patch("accounts.forms.is_safe_ollama_endpoint", side_effect=lambda ip: ip != "10.0.0.1"),
    ):
        success, msg = generate_reflection(
            "ctx", "prompt", "custom", "model", api_base="https://rebind.attacker.com/v1"
        )
        assert success is False
        assert "destination 10.0.0.1 is private or restricted" in msg

    # Disabled / none provider
    assert generate_reflection("ctx", "prompt", "none", "any")[0] is False

    # Invalid API base URL
    assert (
        generate_reflection(
            "ctx", "prompt", "openai", "gpt-4o", api_base="http://api.openai.com/v1"
        )[0]
        is False
    )

    # LiteLLM exception handling and Ollama client session isolation
    sentinel_session = object()
    import litellm

    litellm.client_session = cast(Any, sentinel_session)
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Ollama reflection"))]
    with (
        patch("litellm.completion", return_value=mock_resp) as mock_comp,
        patch("accounts.forms.is_safe_ollama_endpoint", return_value=True),
    ):
        ok, res = generate_reflection("ctx", "prompt", "ollama", "llama3")
        assert ok is True
        assert res == "Ollama reflection"
        # Ensure litellm.client_session was not touched or mutated
        assert litellm.client_session is sentinel_session
        # Ensure client was passed as openai.OpenAI with /v1 endpoint and openai/ model prefix
        call_kwargs = mock_comp.call_args[1]
        assert call_kwargs["model"] == "openai/llama3"
        assert call_kwargs["api_base"].endswith("/v1")
        assert hasattr(call_kwargs["client"], "chat")
    litellm.client_session = None

    with (
        patch("litellm.completion", side_effect=RuntimeError("API down")),
        patch("accounts.forms.is_safe_ollama_endpoint", return_value=True),
    ):
        ok, err = generate_reflection("ctx", "prompt", "ollama", "llama3")
        assert ok is False
        assert "The LLM endpoint could not be reached" in err
        assert "API down" not in err

    # 4. Decisions Admin coverage
    site = AdminSite()
    dec_admin = DecisionRecordAdmin(DecisionRecord, site)
    req = MagicMock()
    req.user = user
    req.user.is_superuser = False

    qs = dec_admin.get_queryset(req)
    assert dec in qs

    dec_other = DecisionRecord(framework=Framework.objects.create(owner=other_user, name="Other"))
    assert dec_admin.has_change_permission(req, dec_other) is False
    assert dec_admin.has_delete_permission(req, dec_other) is False

    # Superuser check
    req.user.is_superuser = True
    assert dec_admin.has_change_permission(req, dec) is True
    assert dec_admin.has_delete_permission(req, dec) is True

    req.user.is_superuser = False
    fw_field = dec_admin.formfield_for_foreignkey(DecisionRecord._meta.get_field("framework"), req)
    assert fw_field.queryset.filter(owner=other_user).count() == 0
    assert fw_field.queryset.filter(owner=user).count() >= 1

    dom_field = dec_admin.formfield_for_manytomany(
        DecisionRecord._meta.get_field("affected_domains"), req
    )
    assert dom_field.queryset.filter(framework__owner=other_user).count() == 0

    why_field = dec_admin.formfield_for_manytomany(
        DecisionRecord._meta.get_field("relevant_whys"), req
    )
    assert why_field.queryset.filter(domain__framework__owner=other_user).count() == 0

    obj_field = dec_admin.formfield_for_manytomany(
        DecisionRecord._meta.get_field("supporting_objectives"), req
    )
    assert obj_field.queryset.filter(primary_domain__framework__owner=other_user).count() == 0

    ref_admin = LLMReflectionLogAdmin(LLMReflectionLog, site)
    ref_qs = ref_admin.get_queryset(req)
    assert ref in ref_qs

    ref_other = LLMReflectionLog(framework=dec_other.framework)
    assert ref_admin.has_change_permission(req, ref_other) is False
    assert ref_admin.has_delete_permission(req, ref_other) is False

    req.user.is_superuser = True
    assert ref_admin.has_change_permission(req, ref) is True
    assert ref_admin.has_delete_permission(req, ref) is True

    req.user.is_superuser = False
    ref_fw_field = ref_admin.formfield_for_foreignkey(
        LLMReflectionLog._meta.get_field("framework"), req
    )
    assert ref_fw_field.queryset.filter(owner=other_user).count() == 0
    assert ref_fw_field.queryset.filter(owner=user).count() >= 1

    ref_dec_field = ref_admin.formfield_for_foreignkey(
        LLMReflectionLog._meta.get_field("decision"), req
    )
    assert ref_dec_field.queryset.filter(framework__owner=other_user).count() == 0

    # 5. SSRFSafeTransport, IP pinning, and redirect prevention
    from llm.service import SSRFSafeTransport, httpx

    transport = SSRFSafeTransport(allowlist=[])
    with pytest.raises(ValueError, match="Outbound connection blocked"):
        http_req1 = httpx.Request("GET", "http://169.254.169.254/latest/meta-data/")
        transport.handle_request(http_req1)
    with pytest.raises(ValueError, match="Outbound connection blocked"):
        http_req2 = httpx.Request("GET", "http://10.0.0.1:8000/v1/chat")
        transport.handle_request(http_req2)
    client_test = httpx.Client(transport=transport, follow_redirects=False)
    assert client_test.follow_redirects is False

    # IP pinning test: request.url is rewritten to safe IP with Host preserved (non-default port)
    req_pin = httpx.Request("GET", "http://localhost:8000/v1/models")
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 8000))],
    ):
        transport_pin = SSRFSafeTransport(allowlist=["localhost"])
        with patch.object(httpx.HTTPTransport, "handle_request", return_value=MagicMock()):
            transport_pin.handle_request(req_pin)
            assert req_pin.url.host == "127.0.0.1"
            assert req_pin.headers["Host"] == "localhost:8000"

    # HTTPS IP pinning test: sni_hostname is set without port, Host preserves non-default port
    req_ssl = httpx.Request("GET", "https://localhost:8443/v1/models")
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 8443))],
    ):
        transport_pin = SSRFSafeTransport(allowlist=["localhost"])
        with patch.object(httpx.HTTPTransport, "handle_request", return_value=MagicMock()):
            transport_pin.handle_request(req_ssl)
            assert req_ssl.url.host == "127.0.0.1"
            assert req_ssl.headers["Host"] == "localhost:8443"
            assert req_ssl.extensions.get("sni_hostname") == "localhost"

    # Default port test: port 80/443 is omitted from Host header
    req_def = httpx.Request("GET", "http://localhost:80/v1/models")
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    ):
        transport_pin = SSRFSafeTransport(allowlist=["localhost"])
        with patch.object(httpx.HTTPTransport, "handle_request", return_value=MagicMock()):
            transport_pin.handle_request(req_def)
            assert req_def.headers["Host"] == "localhost"

    # 6. Settings cookie types
    from django.conf import settings

    assert isinstance(settings.SESSION_COOKIE_SECURE, bool)
    assert isinstance(settings.CSRF_COOKIE_SECURE, bool)


def test_compare_view_security_and_edge_cases(
    client, user, other_user, framework, objective, goal
):
    from frameworks.models import Domain, Framework, Objective

    client.force_login(user)

    # 1. Cross-user isolation: accessing another user's framework returns 404
    other_fw = Framework.objects.create(owner=other_user, name="Other Framework")
    resp_other = client.get(f"/decisions/compare/{other_fw.id}/")
    assert resp_other.status_code == 404

    # 2. Foreign selected IDs: foreign objective ID in selected is excluded from items
    other_dom = Domain.objects.create(framework=other_fw, name="Other Domain")
    other_obj = Objective.objects.create(primary_domain=other_dom, title="Foreign Obj")
    resp_foreign = client.get(
        f"/decisions/compare/{framework.id}/?type=objectives&selected={objective.id}&selected={other_obj.id}"
    )
    assert resp_foreign.status_code == 200
    assert objective in resp_foreign.context["items"]
    assert other_obj not in resp_foreign.context["items"]

    # 3. Invalid compare_type falls back to "objectives"
    resp_invalid_type = client.get(
        f"/decisions/compare/{framework.id}/?type=malicious_type&selected={objective.id}"
    )
    assert resp_invalid_type.status_code == 200
    assert resp_invalid_type.context["compare_type"] == "objectives"

    # 4. POST vs GET selected precedence: POST body overrides query string with distinct IDs
    obj_post = Objective.objects.create(
        primary_domain=objective.primary_domain, title="POST Selected Only"
    )
    resp_precedence = client.post(
        f"/decisions/compare/{framework.id}/?selected={objective.id}",
        {
            "action": "convert_to_decision",
            "type": "objectives",
            "selected": [str(obj_post.id)],
        },
    )
    assert resp_precedence.status_code == 302
    created_dec = DecisionRecord.objects.filter(
        framework=framework, title__contains="POST Selected Only"
    ).first()
    assert created_dec is not None
    assert obj_post in created_dec.supporting_objectives.all()
    assert objective not in created_dec.supporting_objectives.all()

    # 5. Empty selection: POST with empty selected shows warning, no DecisionRecord created
    initial_count = DecisionRecord.objects.filter(framework=framework).count()
    resp_empty = client.post(
        f"/decisions/compare/{framework.id}/",
        {
            "action": "convert_to_decision",
            "type": "objectives",
            "selected": [],
        },
        follow=True,
    )
    assert resp_empty.status_code == 200
    assert DecisionRecord.objects.filter(framework=framework).count() == initial_count
    messages = list(resp_empty.context["messages"])
    assert any("select at least one" in m.message.lower() for m in messages)

    # 6. Empty selection on reflection does not call LLM
    with patch("decisions.views.generate_reflection") as mock_gen:
        resp_empty_reflect = client.post(
            f"/decisions/compare/{framework.id}/",
            {
                "action": "reflect",
                "type": "objectives",
                "selected": [],
            },
            follow=True,
        )
        assert resp_empty_reflect.status_code == 200
        assert not mock_gen.called


def test_mark_all_reviewed_and_move_methods(client, user, other_user, framework, domain, why):
    client.force_login(user)

    # 1. mark_all_reviewed_view requires POST (GET returns 403)
    resp_get = client.get(f"/frameworks/review/{framework.id}/mark-all/")
    assert resp_get.status_code == 403

    # 2. Cross-user isolation on mark_all_reviewed_view
    client.force_login(other_user)
    resp_cross = client.post(f"/frameworks/review/{framework.id}/mark-all/")
    assert resp_cross.status_code == 404

    # 3. domain_move_view requires POST (GET returns 403)
    client.force_login(user)
    assert client.get(f"/frameworks/domain/{domain.id}/move/up/").status_code == 403

    # 4. why_move_view requires POST (GET returns 403)
    assert client.get(f"/frameworks/why/{why.id}/move/up/").status_code == 403

    # 5. Invalid direction on move leaves items unchanged
    initial_order = domain.display_order
    resp_invalid_dir = client.post(f"/frameworks/domain/{domain.id}/move/sideways/")
    assert resp_invalid_dir.status_code == 302
    domain.refresh_from_db()
    assert domain.display_order == initial_order


def test_chat_view_selected_decisions_filtering(client, user, framework):
    client.force_login(user)
    cfg, _ = UserLLMConfig.objects.get_or_create(user=user)
    cfg.consent_given = True
    cfg.provider = "ollama"
    cfg.model_name = "llama3.1"
    cfg.save()

    dec1 = DecisionRecord.objects.create(
        framework=framework, title="Decision Alpha", proposal_description="Alpha desc"
    )
    DecisionRecord.objects.create(
        framework=framework, title="Decision Beta", proposal_description="Beta desc"
    )

    with patch("llm.views.generate_reflection", return_value=(True, "Chat response")) as mock_gen:
        resp = client.post(
            f"/llm/framework/{framework.id}/chat/",
            {
                "prompt": "How does Alpha fit?",
                "selected_decisions": [str(dec1.id)],
            },
        )
        assert resp.status_code == 302
        assert mock_gen.called
        ctx = mock_gen.call_args[1]["user_context_markdown"]
        assert "Decision Assessment: Decision Alpha" in ctx
        assert "Decision Assessment: Decision Beta" not in ctx


def test_test_llm_connection_key_isolation_on_api_base_change(client, user):
    client.force_login(user)
    cfg, _ = UserLLMConfig.objects.get_or_create(user=user)
    cfg.consent_given = True
    cfg.provider = "custom"
    cfg.model_name = "custom-model"
    cfg.api_base = "https://legit-server.internal/v1"
    cfg.api_key = "super-secret-key-12345"
    cfg.save()

    # Changing api_base without api_key in POST does NOT reuse stored key (prevents exfiltration)
    with patch("llm.service.generate_reflection") as mock_gen:
        mock_gen.return_value = (True, "Connection OK")
        with patch(
            "accounts.forms.validate_llm_api_base", return_value="https://attacker-server.com/v1"
        ):
            resp = client.post(
                "/accounts/settings/test-llm/",
                {
                    "provider": "custom",
                    "model_name": "custom-model",
                    "api_base": "https://attacker-server.com/v1",
                    "api_key": "",
                    "consent_given": True,
                },
            )
            assert resp.status_code == 302
            assert mock_gen.called
            # Key sent to generate_reflection must be None/empty, NOT super-secret-key-12345!
            assert mock_gen.call_args[1]["api_key"] in (None, "")


def test_reflection_delete_redirects_to_decision_detail_when_set(client, user, framework):
    client.force_login(user)
    dec = DecisionRecord.objects.create(
        framework=framework, title="Delete Ref Test", proposal_description="Desc"
    )
    ref = LLMReflectionLog.objects.create(
        framework=framework,
        decision=dec,
        user_prompt="Prompt",
        context_snapshot="Ctx",
        llm_response="Resp",
        provider_used="ollama",
    )
    # Deleting decision reflection redirects to decision detail
    resp = client.post(f"/llm/reflection/{ref.id}/delete/")
    assert resp.status_code == 302
    assert resp.url == f"/decisions/{dec.id}/"
    assert not LLMReflectionLog.objects.filter(id=ref.id).exists()


def test_settings_view_clears_api_key_when_api_base_changes(client, user):
    client.force_login(user)
    cfg, _ = UserLLMConfig.objects.get_or_create(user=user)
    cfg.provider = "custom"
    cfg.model_name = "custom-model"
    cfg.api_base = "https://legit-server.internal/v1"
    cfg.api_key = "super-secret-key-12345"
    cfg.save()

    # Changing api_base without providing a raw_api_key clears api_key
    with patch(
        "accounts.forms.validate_llm_api_base", return_value="https://new-server.internal/v1"
    ):
        resp = client.post(
            "/accounts/settings/",
            {
                "provider": "custom",
                "model_name": "custom-model",
                "api_base": "https://new-server.internal/v1",
                "raw_api_key": "",
                "consent_given": True,
                "theme_preference": "auto",
            },
        )
        assert resp.status_code == 302
        cfg.refresh_from_db()
        assert cfg.api_base == "https://new-server.internal/v1"
        assert cfg.api_key == ""


def test_cookie_secure_settings_env_parsing(monkeypatch):
    import importlib

    import config.settings

    # Test "yes" / "1" -> True
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "yes")
    monkeypatch.setenv("CSRF_COOKIE_SECURE", "1")
    importlib.reload(config.settings)
    assert config.settings.SESSION_COOKIE_SECURE is True
    assert config.settings.CSRF_COOKIE_SECURE is True

    # Test "false" / "0" -> False
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("CSRF_COOKIE_SECURE", "0")
    importlib.reload(config.settings)
    assert config.settings.SESSION_COOKIE_SECURE is False
    assert config.settings.CSRF_COOKIE_SECURE is False

    # Restore default settings
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("CSRF_COOKIE_SECURE", raising=False)
    importlib.reload(config.settings)


def test_user_llm_config_form_retained_api_key_validation(user):
    from accounts.forms import UserLLMConfigForm
    from accounts.models import UserLLMConfig

    cfg, _ = UserLLMConfig.objects.get_or_create(user=user)
    cfg.provider = "ollama"
    cfg.model_name = "llama3.1"
    cfg.api_base = "http://remote-ollama.example.com:11434/v1"
    cfg.api_key = "secret-ollama-key"
    cfg.save()

    # Case 1: Keeping the same provider and api_base with blank raw_api_key retains the key.
    # Remote HTTP Ollama with an API key must fail validation.
    with patch("accounts.forms.is_safe_ollama_endpoint", return_value=True):
        form = UserLLMConfigForm(
            data={
                "provider": "ollama",
                "model_name": "llama3.1",
                "api_base": "http://remote-ollama.example.com:11434/v1",
                "raw_api_key": "",
                "consent_given": True,
                "theme_preference": "auto",
            },
            instance=cfg,
        )
        assert not form.is_valid()
        assert "api_base" in form.errors
        assert "Ollama remote API base URL must use HTTPS when an API key is configured" in str(
            form.errors["api_base"]
        )

    # Case 2: Changing api_base with blank raw_api_key does NOT retain the old key.
    # Remote HTTP Ollama without an API key is permitted.
    with patch("accounts.forms.is_safe_ollama_endpoint", return_value=True):
        form2 = UserLLMConfigForm(
            data={
                "provider": "ollama",
                "model_name": "llama3.1",
                "api_base": "http://other-remote-ollama.example.com:11434/v1",
                "raw_api_key": "",
                "consent_given": True,
                "theme_preference": "auto",
            },
            instance=cfg,
        )
        assert form2.is_valid(), form2.errors

    # Case 3: Changing provider with blank raw_api_key does not retain saved key across providers.
    # Start with provider "none", a saved key, and a remote HTTP Ollama base.
    cfg.provider = "none"
    cfg.model_name = "none"
    cfg.api_base = "http://remote-ollama.example.com:11434/v1"
    cfg.api_key = "secret-ollama-key"
    cfg.save()

    # Submitting provider "ollama" with same remote HTTP base and blank raw_api_key must be valid,
    # ensuring clean does not reuse the saved key across providers (which would fail validation
    # because remote HTTP Ollama with an API key is prohibited).
    with patch("accounts.forms.is_safe_ollama_endpoint", return_value=True):
        form3 = UserLLMConfigForm(
            data={
                "provider": "ollama",
                "model_name": "llama3.1",
                "api_base": "http://remote-ollama.example.com:11434/v1",
                "raw_api_key": "",
                "consent_given": True,
                "theme_preference": "auto",
            },
            instance=cfg,
        )
        assert form3.is_valid(), form3.errors


def test_dns_rebinding_ssrf_prevention():
    import socket

    from llm.service import SSRFSafeTransport, httpx

    # In production (DEBUG=False), allowlisting a non-loopback host must not permit
    # connecting to loopback if that host resolves to 127.0.0.1 or ::1 via DNS rebinding.
    transport = SSRFSafeTransport(allowlist=["ollama.partner.example"])
    req_v4 = httpx.Request("GET", "http://ollama.partner.example:11434/v1/models")
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434))],
    ):
        with pytest.raises(ValueError, match="Outbound connection blocked"):
            transport.handle_request(req_v4)

    req_v6 = httpx.Request("GET", "http://ollama.partner.example:11434/v1/models")
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 11434))],
    ):
        with pytest.raises(ValueError, match="Outbound connection blocked"):
            transport.handle_request(req_v6)

    # When localhost is allowlisted alongside an external host (F-02),
    # the external host must still NOT be allowed to rebind to 127.0.0.1
    transport_multi = SSRFSafeTransport(allowlist=["localhost", "ollama.partner.example"])
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434))],
    ):
        with pytest.raises(ValueError, match="Outbound connection blocked"):
            transport_multi.handle_request(req_v4)

        # Conversely, a request explicitly targeting localhost IS allowed
        req_local = httpx.Request("GET", "http://localhost:11434/v1/models")
        with patch.object(httpx.HTTPTransport, "handle_request", return_value=MagicMock()):
            resp = transport_multi.handle_request(req_local)
            assert resp is not None

    # When allowlist is empty in production, requests targeting localhost must be blocked
    transport_empty = SSRFSafeTransport(allowlist=[])
    req_local_empty = httpx.Request("GET", "http://localhost:11434/v1/models")
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434))],
    ):
        with pytest.raises(ValueError, match="Outbound connection blocked"):
            transport_empty.handle_request(req_local_empty)

    # Symmetrical loopback allowlist: allowlist=["127.0.0.1"] allows request to localhost
    transport_ip_allowlist = SSRFSafeTransport(allowlist=["127.0.0.1"])
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434))],
    ):
        with patch.object(httpx.HTTPTransport, "handle_request", return_value=MagicMock()):
            resp_sym = transport_ip_allowlist.handle_request(req_local)
            assert resp_sym is not None

    # Specific loopback IP allowlist: allowlist=["127.0.0.2"] allows direct request to 127.0.0.2
    transport_ip2 = SSRFSafeTransport(allowlist=["127.0.0.2"])
    req_local_ip2 = httpx.Request("GET", "http://127.0.0.2:11434/v1/models")
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.2", 11434))],
    ):
        with patch.object(httpx.HTTPTransport, "handle_request", return_value=MagicMock()):
            resp_ip2 = transport_ip2.handle_request(req_local_ip2)
            assert resp_ip2 is not None

    # IPv4-mapped loopback rebinding rejection: external host resolving to ::ffff:127.0.0.1 blocked
    with patch(
        "socket.getaddrinfo",
        return_value=[
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::ffff:127.0.0.1", 11434))
        ],
    ):
        with pytest.raises(ValueError, match="Outbound connection blocked"):
            transport.handle_request(req_v4)


def test_is_loopback_host():
    from accounts.forms import is_loopback_host

    assert is_loopback_host("localhost") is True
    assert is_loopback_host("127.0.0.1") is True
    assert is_loopback_host("127.0.0.2") is True
    assert is_loopback_host("::1") is True
    assert is_loopback_host("::ffff:127.0.0.1") is True
    assert is_loopback_host("example.com") is False
    assert is_loopback_host("192.168.1.1") is False
    assert is_loopback_host("8.8.8.8") is False


def test_unc_sqlite_database_migration(tmp_path):
    import sqlite3

    from config.settings import migrate_legacy_sqlite_database

    user_data_dir = tmp_path / "user_data"
    temp_dir = tmp_path / "legacy_temp"
    temp_dir.mkdir()
    legacy_db = temp_dir / "prioritysuite_dev.sqlite3"

    # 1. Create a valid legacy SQLite database with table and data
    src_conn = sqlite3.connect(str(legacy_db))
    src_conn.execute("CREATE TABLE test_data (id INT, val TEXT);")
    src_conn.execute("INSERT INTO test_data VALUES (1, 'initial_val');")
    src_conn.commit()
    src_conn.close()

    # Migrate legacy database to user data directory
    result_path = migrate_legacy_sqlite_database(user_data_dir, temp_dir)
    assert result_path.exists()
    assert result_path == user_data_dir / "prioritysuite_dev.sqlite3"

    # Verify contents of migrated database
    dest_conn = sqlite3.connect(str(result_path))
    rows = dest_conn.execute("SELECT id, val FROM test_data;").fetchall()
    dest_conn.close()
    assert rows == [(1, "initial_val")]

    # 2. When destination already exists, helper must leave it unchanged
    src_conn2 = sqlite3.connect(str(legacy_db))
    src_conn2.execute("UPDATE test_data SET val = 'updated_in_legacy' WHERE id = 1;")
    src_conn2.commit()
    src_conn2.close()

    result_path2 = migrate_legacy_sqlite_database(user_data_dir, temp_dir)
    assert result_path2 == result_path
    dest_conn2 = sqlite3.connect(str(result_path2))
    rows2 = dest_conn2.execute("SELECT id, val FROM test_data;").fetchall()
    dest_conn2.close()
    assert rows2 == [(1, "initial_val")]

    # 3. Migration failure before backup creates staging file
    failing_user_data = tmp_path / "failing_user_data"
    with patch("sqlite3.connect", side_effect=sqlite3.OperationalError("disk I/O error")):
        with pytest.raises(RuntimeError, match="Failed to migrate legacy SQLite database"):
            migrate_legacy_sqlite_database(failing_user_data, temp_dir)

    target_failed_path = failing_user_data / "prioritysuite_dev.sqlite3"
    assert not target_failed_path.exists()
    assert list(failing_user_data.glob("*.tmp")) == []

    # 4. Publication failure (Path.replace fails after backup completes):
    # helper must remove staging file, preserve legacy database, and raise RuntimeError
    pub_fail_user_data = tmp_path / "pub_fail_user_data"
    with patch("pathlib.Path.replace", side_effect=OSError("Permission denied")):
        with pytest.raises(RuntimeError, match="Failed to migrate legacy SQLite database"):
            migrate_legacy_sqlite_database(pub_fail_user_data, temp_dir)

    pub_failed_target = pub_fail_user_data / "prioritysuite_dev.sqlite3"
    assert not pub_failed_target.exists()
    assert list(pub_fail_user_data.glob("*.tmp")) == []
    assert legacy_db.exists()
    src_conn3 = sqlite3.connect(str(legacy_db))
    rows3 = src_conn3.execute("SELECT id, val FROM test_data;").fetchall()
    src_conn3.close()
    assert rows3 == [(1, "updated_in_legacy")]

    # 5. Process-shared lock serialization: if destination created while waiting on lock
    race_user_data = tmp_path / "race_user_data"
    race_user_data.mkdir()
    race_target_db = race_user_data / "prioritysuite_dev.sqlite3"
    race_target_db.write_text("already-migrated")
    res_race = migrate_legacy_sqlite_database(race_user_data, temp_dir)
    assert res_race == race_target_db
    assert race_target_db.read_text() == "already-migrated"


def test_offline_allowlisted_sidecar_endpoint(settings):
    import socket

    from accounts.forms import is_safe_ollama_endpoint

    settings.DEBUG = False
    settings.OLLAMA_ALLOWED_HOSTS = ["ollama.offline-sidecar.local"]

    # Even if DNS resolution for the offline sidecar fails with gaierror,
    # the allowlisted hostname must be accepted by form validation.
    with patch("socket.getaddrinfo", side_effect=socket.gaierror("NXDOMAIN")):
        assert is_safe_ollama_endpoint("ollama.offline-sidecar.local") is True


def test_shared_sanitization_helpers():
    from llm.service import sanitize_credentials, sanitize_url

    url_with_auth = "https://user:secretpass@api.example.com/v1"
    assert sanitize_url(url_with_auth) == "https://api.example.com/v1"
    assert sanitize_url("http://api.example.com:8080/v1") == "http://api.example.com:8080/v1"
    assert sanitize_url("") == "[default]"
    assert sanitize_url(None) == "[default]"
    assert sanitize_url("http://[invalid:url") == "[invalid-url]"

    msg = "Connection failed with key sk-secret123 and auth https://user:pass456@api.com"
    sanitized = sanitize_credentials(
        msg,
        api_key="sk-secret123",
        api_base="https://user:pass456@api.com",
    )
    assert "sk-secret123" not in sanitized
    assert "pass456" not in sanitized
    assert "[REDACTED]" in sanitized


def test_accounts_forms_endpoint_safety(settings):
    import ipaddress
    import socket

    from accounts.forms import (
        _is_ip_address_safe,
        is_restricted_ip,
        is_safe_ollama_endpoint,
    )

    # 1. IPv4-mapped IPv6 address handling
    mapped_ip = ipaddress.ip_address("::ffff:127.0.0.1")
    assert is_restricted_ip(mapped_ip) is False
    settings.DEBUG = True
    assert _is_ip_address_safe(mapped_ip) is True
    settings.DEBUG = False
    assert _is_ip_address_safe(mapped_ip) is False

    # 2. Metadata hosts
    assert is_safe_ollama_endpoint("169.254.169.254") is False

    # 3. Allowlist with raw IP endpoints
    settings.OLLAMA_ALLOWED_HOSTS = ["127.0.0.1", "169.254.169.254"]
    settings.DEBUG = False
    # 169.254.169.254 is restricted metadata, blocked even if allowlisted
    assert is_safe_ollama_endpoint("169.254.169.254") is False
    # 127.0.0.1 is allowlisted
    assert is_safe_ollama_endpoint("127.0.0.1") is True

    # Explicitly allowlisted non-standard loopback address (e.g. 127.0.0.2)
    settings.OLLAMA_ALLOWED_HOSTS = ["127.0.0.2"]
    assert is_safe_ollama_endpoint("127.0.0.2") is True

    # Allowlist without loopback in production blocks loopback
    settings.OLLAMA_ALLOWED_HOSTS = ["ollama.prod.example"]
    assert is_safe_ollama_endpoint("127.0.0.1") is False

    # 4. Default settings: OLLAMA_ALLOWED_HOSTS is [] (empty list)
    settings.OLLAMA_ALLOWED_HOSTS = []
    settings.DEBUG = False
    assert is_safe_ollama_endpoint("8.8.8.8") is True
    from accounts.forms import validate_llm_api_base

    valid_base = validate_llm_api_base("custom", "https://8.8.8.8/v1")
    assert valid_base == "https://8.8.8.8/v1"
    assert is_safe_ollama_endpoint("10.0.0.1") is False
    assert is_safe_ollama_endpoint("127.0.0.1") is False
    assert is_safe_ollama_endpoint("::ffff:127.0.0.1") is False
    assert is_safe_ollama_endpoint("localhost") is False

    # 5. Fallback when OLLAMA_ALLOWED_HOSTS is None
    settings.OLLAMA_ALLOWED_HOSTS = None
    settings.DEBUG = True
    assert is_safe_ollama_endpoint("localhost") is True
    settings.DEBUG = False
    assert is_safe_ollama_endpoint("localhost") is False
    assert is_safe_ollama_endpoint("10.0.0.1") is False
    assert is_safe_ollama_endpoint("8.8.8.8") is True

    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 11434))],
    ):
        assert is_safe_ollama_endpoint("remote.public.example") is True

    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 11434))],
    ):
        assert is_safe_ollama_endpoint("internal.private.example") is False

    with patch("socket.getaddrinfo", side_effect=socket.gaierror("lookup error")):
        assert is_safe_ollama_endpoint("invalid.domain.xyz") is False
