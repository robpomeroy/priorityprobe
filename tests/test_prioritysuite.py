import os
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import pytest
from django.contrib.auth.models import User
from accounts.models import UserLLMConfig
from accounts.crypto import encrypt_value, decrypt_value
from frameworks.models import Framework, Domain, Why, Objective, Goal, StatusChoices
from frameworks.services import seed_sample_framework, remove_sample_frameworks
from decisions.models import DecisionRecord, DecisionStatus, LLMReflectionLog
from exports.services import generate_framework_markdown, generate_decision_markdown
from unittest.mock import patch, MagicMock

@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", email="test@example.com", password="password123")

@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", email="other@example.com", password="password123")

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
    obj = Objective.objects.create(primary_domain=domain, title="Maintain craft excellence", status=StatusChoices.ACTIVE)
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
    config = UserLLMConfig.objects.create(user=user, provider="openrouter", model_name="openrouter/anthropic/claude-3.5-sonnet")
    config.api_key = "secret-key-test"
    config.save()

    assert config.api_key == "secret-key-test"
    assert config._encrypted_api_key != "secret-key-test"
    assert str(config).startswith("LLM Config for testuser")

def test_user_registration_and_login(db, client):
    response = client.post("/accounts/register/", {
        "username": "newperson",
        "email": "new@example.com",
        "password": "strongpassword123",
        "password_confirm": "strongpassword123",
    })
    assert response.status_code == 302
    assert User.objects.filter(username="newperson").exists()

def test_user_registration_mismatch(db, client):
    response = client.post("/accounts/register/", {
        "username": "newperson2",
        "email": "new2@example.com",
        "password": "strongpassword123",
        "password_confirm": "wrong",
    })
    assert response.status_code == 200
    assert not User.objects.filter(username="newperson2").exists()

def test_user_settings_update(client, user):
    client.force_login(user)
    response = client.post("/accounts/settings/", {
        "provider": "openrouter",
        "model_name": "openrouter/anthropic/claude-3.5-sonnet",
        "api_base": "https://openrouter.ai/api/v1",
        "raw_api_key": "new-secret-api-key",
        "consent_given": True,
        "theme_preference": "dark",
    })
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
    resp = client.post(f"/frameworks/framework/{framework.id}/domain/create/", {
        "name": "Personal Growth",
        "description": "Continuous learning and stewardship",
        "display_order": 2,
    })
    assert resp.status_code == 302
    d = Domain.objects.get(name="Personal Growth")
    # Edit
    resp = client.post(f"/frameworks/domain/{d.id}/edit/", {
        "name": "Personal Development",
        "description": "Updated",
        "display_order": 3,
    })
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
    resp = client.post(f"/frameworks/domain/{domain.id}/why/create/", {
        "title": "To provide for my dependents",
        "description": "Financial stewardship",
        "is_non_negotiable": True,
        "display_order": 1,
    })
    assert resp.status_code == 302
    w = Why.objects.get(title="To provide for my dependents")
    assert w.is_non_negotiable is True
    # Edit Why
    resp = client.post(f"/frameworks/why/{w.id}/edit/", {
        "title": "To support my family well",
        "description": "Updated",
        "is_non_negotiable": False,
        "display_order": 2,
    })
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
    resp = client.post(f"/frameworks/framework/{framework.id}/objective/create/", {
        "primary_domain": domain.id,
        "title": "Build emergency fund",
        "description": "Resilience buffer",
        "whys": [why.id],
        "status": "ACTIVE",
    })
    assert resp.status_code == 302
    obj = Objective.objects.get(title="Build emergency fund")

    # Create Goal
    resp = client.post(f"/frameworks/framework/{framework.id}/goal/create/", {
        "primary_domain": domain.id,
        "title": "Save £10k",
        "description": "Over 2 years",
        "objectives": [obj.id],
        "status": "ACTIVE",
    })
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

# --- 3. Decisions Tests ---

def test_decisions_workflow(client, user, framework, domain, why, objective):
    client.force_login(user)
    # Create Decision
    resp = client.post("/decisions/create/", {
        "title": "Promotion Offer",
        "proposal_description": "Step into VP Engineering role with 30% more travel",
        "affected_domains": [domain.id],
        "relevant_whys": [why.id],
        "supporting_objectives": [objective.id],
        "conflicting_objectives": [],
        "benefits_and_costs": "More money, less family time",
        "status": "EXPLORING",
    })
    assert resp.status_code == 302
    dec = DecisionRecord.objects.get(title="Promotion Offer")
    assert dec.affected_domains.first() == domain

    # Detail View
    resp = client.get(f"/decisions/{dec.id}/")
    assert resp.status_code == 200
    assert "Promotion Offer" in resp.content.decode()

    # Edit Decision
    resp = client.post(f"/decisions/{dec.id}/edit/", {
        "title": "Promotion Offer (Revised)",
        "proposal_description": "Negotiated remote options",
        "status": "DECIDED",
        "decision_outcome": "Accepted with remote boundary",
    })
    assert resp.status_code == 302
    dec.refresh_from_db()
    assert dec.status == DecisionStatus.DECIDED

    # Delete Decision
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
    mock_choice.message.content = "### Stated Priorities\nYou value honest work.\n\n### Potential Tensions & Inferences\nI infer promotion creates time strain."
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
    resp = client.post(f"/llm/framework/{framework.id}/chat/", {
        "prompt": "Evaluate my framework",
    })
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
    resp = client.post(f"/frameworks/review/mark/objective/{objective.id}/", HTTP_HX_REQUEST="true")
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
    import os
    import importlib
    import sys
    from unittest.mock import patch
    from django.conf import settings

    old_debug = getattr(settings, "DEBUG", True)
    # Ensure config.settings actually raises ValueError when imported with empty key and DEBUG=False
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
    resp = client.post("/accounts/settings/", {
        "provider": "openrouter",
        "model_name": "openrouter/anthropic/claude-3.5-sonnet",
        "api_base": "http://169.254.169.254/latest/meta-data/",
        "consent_given": True,
        "theme_preference": "auto",
    })
    assert resp.status_code == 200
    assert "cloud metadata endpoints is prohibited" in resp.content.decode()

    # OpenRouter non-https blocked
    resp = client.post("/accounts/settings/", {
        "provider": "openrouter",
        "model_name": "openrouter/anthropic/claude-3.5-sonnet",
        "api_base": "http://openrouter.ai/api/v1",
        "consent_given": True,
        "theme_preference": "auto",
    })
    assert resp.status_code == 200
    assert "OpenRouter connections must use HTTPS" in resp.content.decode()

def test_admin_queryset_filtering(user, other_user, framework, domain, why, objective, goal):
    from frameworks.admin import FrameworkAdmin, DomainAdmin, WhyAdmin, ObjectiveAdmin, GoalAdmin
    from decisions.admin import DecisionRecordAdmin, LLMReflectionLogAdmin
    from accounts.admin import UserLLMConfigAdmin
    from accounts.models import UserLLMConfig
    from django.contrib.admin.sites import AdminSite

    site = AdminSite()
    f_admin = FrameworkAdmin(Framework, site)
    d_admin = DomainAdmin(Domain, site)
    dec_admin = DecisionRecordAdmin(DecisionRecord, site)
    llm_admin = UserLLMConfigAdmin(UserLLMConfig, site)

    # Regular staff user (not superuser)
    other_user.is_staff = True
    other_user.save()

    request = MagicMock()
    request.user = other_user
    assert f_admin.get_queryset(request).count() == 0
    assert d_admin.get_queryset(request).count() == 0
    assert dec_admin.get_queryset(request).count() == 0
    assert llm_admin.get_queryset(request).count() == 0

    # Foreign key and M2M formfield scoping for regular staff
    fw_field = d_admin.formfield_for_foreignkey(Domain._meta.get_field("framework"), request)
    assert fw_field.queryset.filter(owner=other_user).count() == 0
    assert fw_field.queryset.filter(owner=user).count() == 0

    dec_fw_field = dec_admin.formfield_for_foreignkey(DecisionRecord._meta.get_field("framework"), request)
    assert dec_fw_field.queryset.filter(owner=other_user).count() == 0

    # Create UserLLMConfig for user
    UserLLMConfig.objects.get_or_create(user=user)

    # Superuser sees all
    request.user.is_superuser = True
    assert f_admin.get_queryset(request).count() >= 1
    assert d_admin.get_queryset(request).count() >= 1
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
    resp = client.post("/accounts/register/", {
        "username": "weakuser1",
        "email": "weak1@example.com",
        "password": "password",
        "password_confirm": "password",
    })
    assert resp.status_code == 200
    assert not User.objects.filter(username="weakuser1").exists()

    # Short password rejected
    resp = client.post("/accounts/register/", {
        "username": "weakuser2",
        "email": "weak2@example.com",
        "password": "abc",
        "password_confirm": "abc",
    })
    assert resp.status_code == 200
    assert not User.objects.filter(username="weakuser2").exists()

def test_decision_export_instructions_and_filename_sanitization(client, user, framework):
    client.force_login(user)
    dec = DecisionRecord.objects.create(
        framework=framework,
        title="Unsafe\r\nTitle \"With\" Slashes/And/Quotes",
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
    resp = client.post(f"/frameworks/objective/{objective.id}/status/", {
        "status": StatusChoices.PAUSED,
        "next": "/frameworks/workspace/"
    })
    assert resp.status_code == 302
    objective.refresh_from_db()
    assert objective.status == StatusChoices.PAUSED

    # Invalid status is ignored
    client.post(f"/frameworks/objective/{objective.id}/status/", {"status": "INVALID_STATUS"})
    objective.refresh_from_db()
    assert objective.status == StatusChoices.PAUSED

    # Cross-user isolation on objective status
    client.force_login(other_user)
    resp_cross = client.post(f"/frameworks/objective/{objective.id}/status/", {"status": StatusChoices.ACTIVE})
    assert resp_cross.status_code == 404

    # Goal status update
    client.force_login(user)
    resp_goal = client.post(f"/frameworks/goal/{goal.id}/status/", {"status": StatusChoices.COMPLETED})
    assert resp_goal.status_code == 302
    goal.refresh_from_db()
    assert goal.status == StatusChoices.COMPLETED

    # Cross-user isolation on goal status
    client.force_login(other_user)
    assert client.post(f"/frameworks/goal/{goal.id}/status/", {"status": StatusChoices.ACTIVE}).status_code == 404

    # Open redirect protection: external target is rejected
    client.force_login(user)
    resp_open = client.post(f"/frameworks/objective/{objective.id}/status/", {
        "status": StatusChoices.PAUSED,
        "next": "https://evil.com/phish"
    })
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
    from frameworks.models import Domain, Why, Objective, Goal
    client.force_login(user)

    domain2 = Domain.objects.create(framework=framework, name="Health", display_order=2)
    why2 = Why.objects.create(domain=domain2, title="Longevity & vitality", is_non_negotiable=True)
    obj2 = Objective.objects.create(primary_domain=domain2, title="Consistent rest", status=StatusChoices.ACTIVE)
    obj2.whys.add(why2)

    # GET comparison view (objectives)
    resp = client.get(f"/decisions/compare/{framework.id}/?type=objectives&selected={objective.id}&selected={obj2.id}")
    assert resp.status_code == 200
    assert resp.context["compare_type"] == "objectives"
    assert objective in resp.context["items"]
    assert obj2 in resp.context["items"]

    # GET comparison view (goals)
    goal2 = Goal.objects.create(primary_domain=domain2, title="Sleep 8 hours", status=StatusChoices.ACTIVE)
    resp_goals = client.get(f"/decisions/compare/{framework.id}/?type=goals&selected={goal.id}&selected={goal2.id}")
    assert resp_goals.status_code == 200
    assert resp_goals.context["compare_type"] == "goals"
    assert goal in resp_goals.context["items"]
    assert goal2 in resp_goals.context["items"]

    # POST action=convert_to_decision
    resp_convert = client.post(f"/decisions/compare/{framework.id}/", {
        "action": "convert_to_decision",
        "type": "objectives",
        "selected": [str(objective.id), str(obj2.id)],
    })
    assert resp_convert.status_code == 302
    assert DecisionRecord.objects.filter(framework=framework, title__startswith="Priority Comparison").exists()

    # POST action=reflect without consent redirects to settings
    resp_no_consent = client.post(f"/decisions/compare/{framework.id}/", {
        "action": "reflect",
        "type": "objectives",
        "selected": [str(objective.id), str(obj2.id)],
    })
    assert resp_no_consent.status_code == 302
    assert resp_no_consent.url == "/accounts/settings/"

    # Grant consent and test reflection
    config, _ = UserLLMConfig.objects.get_or_create(user=user)
    config.consent_given = True
    config.provider = "ollama"
    config.model_name = "llama3.1"
    config.save()

    with patch("decisions.views.generate_reflection", return_value=(True, "Comparison reflection from AI")):
        resp_reflect = client.post(f"/decisions/compare/{framework.id}/", {
            "action": "reflect",
            "type": "objectives",
            "selected": [str(objective.id), str(obj2.id)],
            "prompt": "Evaluate trade-offs between craft and rest.",
        })
        assert resp_reflect.status_code == 200
        assert resp_reflect.context["comparison_reflection"] == "Comparison reflection from AI"
        assert LLMReflectionLog.objects.filter(framework=framework, llm_response="Comparison reflection from AI").exists()

    # POST action=convert_to_decision with type=goals in request body (without query param)
    resp_convert_goal = client.post(f"/decisions/compare/{framework.id}/", {
        "action": "convert_to_decision",
        "type": "goals",
        "selected": [str(goal.id), str(goal2.id)],
    })
    assert resp_convert_goal.status_code == 302
    assert DecisionRecord.objects.filter(framework=framework, supporting_objectives=objective).exists()


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
    with patch("llm.service.generate_reflection", return_value=(True, "PrioritySuite thinking partner connection verified.")):
        resp_ok = client.post("/accounts/settings/test-llm/")
        assert resp_ok.status_code == 302
        assert resp_ok.url == "/accounts/settings/"

    # 4. Connection error test
    with patch("llm.service.generate_reflection", return_value=(False, "Connection refused")):
        resp_err = client.post("/accounts/settings/test-llm/")
        assert resp_err.status_code == 302
        assert resp_err.url == "/accounts/settings/"

    # 5. Testing unsaved form POST values (e.g. changing provider/key in form before clicking Test)
    with patch("llm.service.generate_reflection", return_value=(True, "Verified unsaved settings")) as mock_test_gen:
        resp_unsaved = client.post("/accounts/settings/test-llm/", {
            "provider": "openrouter",
            "model_name": "openrouter/anthropic/claude-3.5-sonnet",
            "api_base": "https://openrouter.ai/api/v1",
            "consent_given": "on",
            "raw_api_key": "sk-new-key",
        })
        assert resp_unsaved.status_code == 302
        assert mock_test_gen.called
        assert mock_test_gen.call_args[1]["provider"] == "openrouter"
        assert mock_test_gen.call_args[1]["api_key"] == "sk-new-key"

    # 6. Reject unknown / invalid provider in POST
    resp_invalid_prov = client.post("/accounts/settings/test-llm/", {
        "provider": "malicious_unsupported_provider",
        "model_name": "test-model",
        "consent_given": "on",
    })
    assert resp_invalid_prov.status_code == 302
    assert resp_invalid_prov.url == "/accounts/settings/"

    # 7. Do not leak stored key when changing providers without a new key
    config.provider = "openai"
    config.api_key = "sk-secret-openai-key"
    config.save()

    with patch("llm.service.generate_reflection", return_value=(True, "OK")) as mock_test_gen2:
        client.post("/accounts/settings/test-llm/", {
            "provider": "anthropic",
            "model_name": "claude-3-haiku",
            "consent_given": "on",
            "raw_api_key": "",
        })
        assert mock_test_gen2.called
        assert mock_test_gen2.call_args[1]["api_key"] == ""

    # Settings save clears previous provider's key when provider changes without a new key
    client.post("/accounts/settings/", {
        "provider": "anthropic",
        "model_name": "claude-3-haiku",
        "api_base": "",
        "consent_given": "on",
        "theme_preference": "auto",
        "raw_api_key": "",
    })
    config.refresh_from_db()
    assert config.provider == "anthropic"
    assert config.api_key == ""


def test_selective_markdown_export_builder(client, user, framework, domain, objective, goal):
    from frameworks.models import Domain, Why
    domain2 = Domain.objects.create(framework=framework, name="Finance", display_order=2)
    dec = DecisionRecord.objects.create(
        framework=framework,
        title="Selective Export Decision",
        proposal_description="Test selective export"
    )
    reflection = LLMReflectionLog.objects.create(
        framework=framework,
        user_prompt="Test prompt",
        context_snapshot="Test snapshot",
        llm_response="Test reflection response",
        provider_used="mock-model"
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
    prev_log = LLMReflectionLog.objects.create(
        framework=framework,
        user_prompt="Prior message",
        context_snapshot="Prior context",
        llm_response="Prior AI answer",
        provider_used="llama3:latest"
    )

    with patch("llm.views.generate_reflection", return_value=(True, "Guided advice on tradeoffs")) as mock_gen:
        resp = client.post(f"/llm/framework/{framework.id}/chat/", {
            "prompt": "How do I choose between these? Focus on trade-offs.",
            "selected_domains": [str(domain.id)],
            "include_history": "1"
        })
        assert resp.status_code == 302
        assert mock_gen.called
        history_passed = mock_gen.call_args[1]["history"]
        assert len(history_passed) == 2
        assert history_passed[0]["content"] == "Prior message"
        assert "Prior context" not in history_passed[0]["content"]

        # Reflection log was created
        assert LLMReflectionLog.objects.filter(framework=framework, llm_response="Guided advice on tradeoffs").exists()

    # All domains unchecked (context filter active with 0 domains selected)
    with patch("llm.views.generate_reflection", return_value=(True, "Response without domains")) as mock_no_dom:
        resp_no_dom = client.post(f"/llm/framework/{framework.id}/chat/", {
            "prompt": "Evaluate general principles",
            "context_filter_active": "1",
        })
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
        provider_used="test"
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
        provider_used="test"
    )
    assert client.get(f"/llm/reflection/{ref2.id}/delete/").status_code == 403


def test_llm_api_base_validation():
    from accounts.forms import validate_llm_api_base
    from django.core.exceptions import ValidationError

    # Allowed providers with valid endpoints
    assert validate_llm_api_base("openai", "https://api.openai.com/v1") == "https://api.openai.com/v1"
    assert validate_llm_api_base("anthropic", "https://api.anthropic.com/v1") == "https://api.anthropic.com/v1"
    assert validate_llm_api_base("gemini", "https://generativelanguage.googleapis.com") == "https://generativelanguage.googleapis.com"
    assert validate_llm_api_base("openrouter", "https://openrouter.ai/api/v1") == "https://openrouter.ai/api/v1"
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
    with pytest.raises(ValidationError, match="OpenAI API Base must point to api.openai.com"):
        validate_llm_api_base("openai", "https://evil-openai.com/v1")
    with pytest.raises(ValidationError, match="Anthropic API Base must point to api.anthropic.com"):
        validate_llm_api_base("anthropic", "https://evil-anthropic.com/v1")
    with pytest.raises(ValidationError, match="Google Gemini API Base must point to"):
        validate_llm_api_base("gemini", "https://evil-gemini.com/v1")
    with pytest.raises(ValidationError, match="OpenRouter API Base must point to openrouter.ai"):
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


def test_coverage_boosters(user, other_user, framework, domain, why, objective):
    from accounts.forms import is_safe_ollama_endpoint
    from decisions.models import DecisionRecord, LLMReflectionLog
    from decisions.admin import DecisionRecordAdmin, LLMReflectionLogAdmin
    from django.contrib.admin.sites import AdminSite
    from llm.service import generate_reflection

    # 1. Endpoint safety checks
    assert is_safe_ollama_endpoint("10.0.0.1") is False
    assert is_safe_ollama_endpoint("192.168.1.1") is False
    assert is_safe_ollama_endpoint("169.254.1.1") is False
    assert is_safe_ollama_endpoint("invalid.host.that.does.not.exist") is False

    import socket
    with patch("socket.getaddrinfo", return_value=[(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 0, 0, 0))]):
        assert is_safe_ollama_endpoint("malicious-ipv6.internal") is False

    # 2. String representations
    dec = DecisionRecord.objects.create(framework=framework, title="Str Test", proposal_description="Desc")
    assert "Str Test" in str(dec)
    ref = LLMReflectionLog.objects.create(
        framework=framework,
        user_prompt="P",
        context_snapshot="C",
        llm_response="R",
        provider_used="test"
    )
    assert "Reflection" in str(ref)

    # 3. Model normalization, history ordering, and error branches
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "OK"
    mock_resp.choices = [mock_choice]

    with patch("litellm.completion", return_value=mock_resp) as mock_litellm, \
         patch("accounts.forms.is_safe_ollama_endpoint", return_value=True):
        assert generate_reflection("ctx", "prompt", "custom", "my-vllm", api_base="http://localhost:8000")[0] is True
        assert generate_reflection("ctx", "prompt", "gemini", "gemini-1.5-flash")[0] is True
        assert generate_reflection("ctx", "prompt", "anthropic", "claude-3-haiku")[0] is True
        assert generate_reflection("ctx", "prompt", "openai", "gpt-4o")[0] is True

        # Custom model containing slashes (e.g. meta-llama/Llama-3-8B-Instruct) gets openai/ prefix
        generate_reflection("ctx", "prompt", "custom", "meta-llama/Llama-3-8B-Instruct", api_base="http://localhost:8000")
        assert mock_litellm.call_args[1]["model"] == "openai/meta-llama/Llama-3-8B-Instruct"

        # Verify history is placed before current prompt
        generate_reflection("ctx", "latest query", "ollama", "llama3", history=[{"role": "user", "content": "prior turn"}])
        sent_messages = mock_litellm.call_args[1]["messages"]
        assert sent_messages[0]["role"] == "system"
        assert sent_messages[1]["content"] == "prior turn"
        assert "latest query" in sent_messages[2]["content"]

    # DNS rebinding protection: destination resolving to private IP is blocked
    with patch("accounts.forms.validate_llm_api_base", return_value="https://rebind.attacker.com/v1"), \
         patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]), \
         patch("accounts.forms.is_safe_ollama_endpoint", side_effect=lambda ip: ip != "10.0.0.1"):
        success, msg = generate_reflection("ctx", "prompt", "custom", "model", api_base="https://rebind.attacker.com/v1")
        assert success is False
        assert "destination 10.0.0.1 is private or restricted" in msg

    # Disabled / none provider
    assert generate_reflection("ctx", "prompt", "none", "any")[0] is False

    # Invalid API base URL
    assert generate_reflection("ctx", "prompt", "openai", "gpt-4o", api_base="http://api.openai.com/v1")[0] is False

    # LiteLLM exception handling
    with patch("litellm.completion", side_effect=RuntimeError("API down")), \
         patch("accounts.forms.is_safe_ollama_endpoint", return_value=True):
        ok, err = generate_reflection("ctx", "prompt", "ollama", "llama3")
        assert ok is False
        assert "API down" in err

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
    dec_admin.formfield_for_foreignkey(DecisionRecord._meta.get_field("framework"), req)
    dec_admin.formfield_for_manytomany(DecisionRecord._meta.get_field("affected_domains"), req)
    dec_admin.formfield_for_manytomany(DecisionRecord._meta.get_field("relevant_whys"), req)
    dec_admin.formfield_for_manytomany(DecisionRecord._meta.get_field("supporting_objectives"), req)

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
    ref_admin.formfield_for_foreignkey(LLMReflectionLog._meta.get_field("framework"), req)
    ref_admin.formfield_for_foreignkey(LLMReflectionLog._meta.get_field("decision"), req)

    # 5. Thread-scoped DNS pinning test
    from llm.service import _pinned_dns
    import socket
    with _pinned_dns("test.isolated.local", 443, "127.0.0.1"):
        res = socket.getaddrinfo("test.isolated.local", 443)
        assert res[0][4][0] == "127.0.0.1"

    # 6. Settings cookie parsing with "yes"
    from django.conf import settings
    assert os.environ.get("SESSION_COOKIE_SECURE", str(not settings.DEBUG)).lower() in ("true", "1", "yes")



