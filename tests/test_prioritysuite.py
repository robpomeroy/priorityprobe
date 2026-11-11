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

