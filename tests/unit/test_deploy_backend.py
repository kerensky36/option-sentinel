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
}

_VERTEX = ("GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "QUORUM_MODEL")


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


def _deploy_env_vars(fake_gcloud, **overrides) -> dict[str, str]:
    bindir, log = fake_gcloud
    env = {k: v for k, v in os.environ.items() if k not in _VERTEX and k not in _REQUIRED}
    env.update(_REQUIRED)
    env.update(overrides)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    result = subprocess.run(
        ["bash", "scripts/deploy_backend.sh"], cwd=_REPO, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    args = log.read_text().splitlines()
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
