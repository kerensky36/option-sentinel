"""Tests for the Vertex AI env vars passed by scripts/deploy_backend.sh (specs/017 T028).

Runs the real script against a fake `gcloud` that records its arguments.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]

_REQUIRED = {
    "GCP_PROJECT_ID": "my-proj",
    "SCHWAB_CLIENT_ID": "id",
    "SCHWAB_CLIENT_SECRET": "secret",
    "SCHWAB_REDIRECT_URI": "https://x/auth/callback",
    "SCHWAB_AUTH_URL": "https://x/a",
    "SCHWAB_TOKEN_URL": "https://x/t",
    "CLOUD_RUN_SERVICE_ACCOUNT": "option-sentinel-run@my-proj.iam.gserviceaccount.com",
}

_VERTEX = ("GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "QUORUM_MODEL")

# Vars a real local .env may set that would otherwise leak into the subprocess env
# below and shadow the test's fixed values (e.g. deploy_backend.sh prefers
# SCHWAB_REDIRECT_URI_PROD over SCHWAB_REDIRECT_URI when both are present).
_LEAKY = ("SCHWAB_REDIRECT_URI_PROD",)


@pytest.fixture
def fake_gcloud(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "gcloud_args"
    gcloud = bindir / "gcloud"
    gcloud.write_text(
        "#!/usr/bin/env bash\n"
        f'[[ "$1 $2" == "run deploy" ]] && printf "%s\\n" "$@" > "{log}"\n'
        'echo "https://fake.run.app"\n'
    )
    gcloud.chmod(0o755)
    return bindir, log


def _deploy_args(fake_gcloud, **overrides) -> list[str]:
    bindir, log = fake_gcloud
    env = {k: v for k, v in os.environ.items() if k not in _VERTEX and k not in _REQUIRED and k not in _LEAKY}
    env.update(_REQUIRED)
    env.update(overrides)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    result = subprocess.run(
        ["bash", "scripts/deploy_backend.sh"], cwd=_REPO, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return log.read_text().splitlines()


def _deploy_env_vars(fake_gcloud, **overrides) -> dict[str, str]:
    args = _deploy_args(fake_gcloud, **overrides)
    value = args[args.index("--update-env-vars") + 1]
    return dict(pair.split("=", 1) for pair in value.split(","))


def test_vertex_vars_default_from_project_and_region(fake_gcloud):
    env_vars = _deploy_env_vars(fake_gcloud)
    assert env_vars["GOOGLE_GENAI_USE_VERTEXAI"] == "TRUE"
    assert env_vars["GOOGLE_CLOUD_PROJECT"] == "my-proj"
    assert env_vars["GOOGLE_CLOUD_LOCATION"] == "us-central1"
    assert "QUORUM_MODEL" not in env_vars


def test_location_follows_cloud_run_region(fake_gcloud):
    env_vars = _deploy_env_vars(fake_gcloud, CLOUD_RUN_REGION="europe-west1")
    assert env_vars["GOOGLE_CLOUD_LOCATION"] == "europe-west1"


def test_env_values_override_defaults(fake_gcloud):
    env_vars = _deploy_env_vars(
        fake_gcloud,
        GOOGLE_CLOUD_PROJECT="ai-proj",
        GOOGLE_CLOUD_LOCATION="us-east4",
        QUORUM_MODEL="gemini-x",
    )
    assert env_vars["GOOGLE_CLOUD_PROJECT"] == "ai-proj"
    assert env_vars["GOOGLE_CLOUD_LOCATION"] == "us-east4"
    assert env_vars["QUORUM_MODEL"] == "gemini-x"


def test_quorum_can_be_disabled(fake_gcloud):
    env_vars = _deploy_env_vars(fake_gcloud, GOOGLE_GENAI_USE_VERTEXAI="FALSE")
    assert env_vars["GOOGLE_GENAI_USE_VERTEXAI"] == "FALSE"


def test_schwab_vars_still_passed(fake_gcloud):
    env_vars = _deploy_env_vars(fake_gcloud)
    for key in ("SCHWAB_CLIENT_ID", "SCHWAB_REDIRECT_URI", "SCHWAB_AUTH_URL", "SCHWAB_TOKEN_URL"):
        assert env_vars[key] == _REQUIRED[key]


# ── specs/022 FR-507: least privilege + Secret Manager ─────────────────────────

_SECRETS = ("SCHWAB_CLIENT_SECRET", "QUORUM_SEAL_KEY", "LOG_PEPPER")


def test_secrets_mounted_from_secret_manager(fake_gcloud):
    args = _deploy_args(fake_gcloud, QUORUM_SEAL_KEY="k" * 48, LOG_PEPPER="p" * 32)
    mounts = dict(pair.split("=", 1) for pair in args[args.index("--update-secrets") + 1].split(","))
    assert mounts == {
        "SCHWAB_CLIENT_SECRET": "schwab-client-secret:latest",
        "QUORUM_SEAL_KEY": "quorum-seal-key:latest",
        "LOG_PEPPER": "log-pepper:latest",
    }


def test_no_secret_value_on_command_line(fake_gcloud):
    args = _deploy_args(fake_gcloud, QUORUM_SEAL_KEY="k" * 48, LOG_PEPPER="p" * 32)
    joined = "\n".join(args)
    for value in ("secret", "k" * 48, "p" * 32):
        assert f"={value}" not in joined
    env_vars = _deploy_env_vars(fake_gcloud)
    for key in _SECRETS:
        assert key not in env_vars


def test_dedicated_service_account_and_single_instance(fake_gcloud):
    args = _deploy_args(fake_gcloud)
    assert args[args.index("--service-account") + 1] == _REQUIRED["CLOUD_RUN_SERVICE_ACCOUNT"]
    assert args[args.index("--max-instances") + 1] == "1"


def test_concurrency_and_timeout_bounded(fake_gcloud):
    """FR-514: at most 10 requests at once, none longer than 90 s."""
    args = _deploy_args(fake_gcloud)
    assert args[args.index("--concurrency") + 1] == "10"
    assert args[args.index("--timeout") + 1] == "90"


def test_concurrency_and_timeout_overridable(fake_gcloud):
    args = _deploy_args(fake_gcloud, CLOUD_RUN_CONCURRENCY="4", CLOUD_RUN_TIMEOUT="120")
    assert args[args.index("--concurrency") + 1] == "4"
    assert args[args.index("--timeout") + 1] == "120"


def test_daily_cap_passed_through(fake_gcloud):
    assert _deploy_env_vars(fake_gcloud, QUORUM_DAILY_CAP="50")["QUORUM_DAILY_CAP"] == "50"
    assert "QUORUM_DAILY_CAP" not in _deploy_env_vars(fake_gcloud)


def test_missing_service_account_stops_before_deploy(fake_gcloud):
    bindir, log = fake_gcloud
    env = {k: v for k, v in os.environ.items() if k not in _VERTEX and k not in _REQUIRED and k not in _LEAKY}
    env.update({k: v for k, v in _REQUIRED.items() if k != "CLOUD_RUN_SERVICE_ACCOUNT"})
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    result = subprocess.run(["bash", "scripts/deploy_backend.sh"], cwd=_REPO, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "setup_gcp_security.sh" in result.stdout + result.stderr
    assert not log.exists()


# ── specs/022 US4: container, dependencies, redaction ─────────────────────────

def test_container_runs_as_non_root():
    dockerfile = (_REPO / "Dockerfile").read_text()
    users = [line.split()[1] for line in dockerfile.splitlines() if line.startswith("USER ")]
    assert users and users[-1] not in ("root", "0")


def test_python_multipart_past_advisories():
    line = next(l for l in (_REPO / "requirements.txt").read_text().splitlines() if l.startswith("python-multipart=="))
    version = tuple(int(p) for p in line.split("==")[1].split("."))
    assert version >= (0, 0, 31)


def test_audit_script_does_not_require_hashes():
    assert "--require-hashes" not in (_REPO / "scripts" / "audit.sh").read_text()


def test_no_schwab_credential_prefixes_in_specs():
    text = (_REPO / "specs" / "004-stateless-ephemeral-refactor" / "quickstart.md").read_text()
    assert "pDdxXHbCJPCX" not in text
    assert "2wtAiqo9NW3h" not in text
