"""scripts/setup_gcp_security.sh grants least privilege and moves secrets (specs/022 FR-508).

Runs the real script against a fake `gcloud` that logs every call and reports
that nothing exists yet.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SA = "option-sentinel-run@my-proj.iam.gserviceaccount.com"


@pytest.fixture
def run_setup(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "calls"
    stdin_log = tmp_path / "stdin"
    gcloud = bindir / "gcloud"
    gcloud.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$*" >> "{log}"\n'
        f'if [[ "$*" == *"versions add"* ]]; then cat >> "{stdin_log}"; echo >> "{stdin_log}"; fi\n'
        # describe calls fail: nothing exists yet, except the Cloud Run service
        'if [[ "$*" == *" describe "* && "$*" != run\\ services\\ describe* ]]; then exit 1; fi\n'
        "exit 0\n"
    )
    gcloud.chmod(0o755)

    def _run(**env_over):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("SCHWAB_", "QUORUM_", "LOG_PEPPER", "BILLING"))}
        env.update({"GCP_PROJECT_ID": "my-proj", "SCHWAB_CLIENT_SECRET": "real-secret-value"})
        env["OPTION_SENTINEL_NO_DOTENV"] = "1"  # a developer's local .env must not leak in
        env.update(env_over)
        env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
        result = subprocess.run(
            ["bash", "scripts/setup_gcp_security.sh"], cwd=_REPO, env=env, capture_output=True, text=True
        )
        calls = log.read_text().splitlines() if log.exists() else []
        stdin = stdin_log.read_text() if stdin_log.exists() else ""
        return result, calls, stdin

    return _run


def test_only_two_project_roles_and_nothing_removed(run_setup):
    result, calls, _ = run_setup()
    assert result.returncode == 0, result.stdout + result.stderr
    project_roles = sorted(
        c.split("--role=")[1].split()[0] for c in calls if c.startswith("projects add-iam-policy-binding")
    )
    assert project_roles == ["roles/aiplatform.user", "roles/logging.logWriter"]
    assert all(_SA in c for c in calls if c.startswith("projects add-iam-policy-binding"))
    assert not any("remove-iam-policy-binding" in c for c in calls)


def test_secret_accessor_granted_per_secret_only(run_setup):
    _, calls, _ = run_setup()
    granted = sorted(
        c.split()[2] for c in calls if c.startswith("secrets add-iam-policy-binding")
    )
    assert granted == ["log-pepper", "quorum-seal-key", "schwab-client-secret"]
    assert all("roles/secretmanager.secretAccessor" in c for c in calls if c.startswith("secrets add-iam-policy-binding"))


def test_secret_values_go_through_stdin_never_argv(run_setup):
    _, calls, stdin = run_setup()
    assert "real-secret-value" in stdin
    assert not any("real-secret-value" in c for c in calls)
    generated = [line for line in stdin.splitlines() if line and line != "real-secret-value"]
    assert len(generated) == 2 and all(len(v) >= 32 for v in generated)


def test_service_migrated_to_account_and_secrets(run_setup):
    _, calls, _ = run_setup()
    update = next(c for c in calls if c.startswith("run services update"))
    assert f"--service-account={_SA}" in update
    assert "--remove-env-vars=SCHWAB_CLIENT_SECRET,QUORUM_SEAL_KEY,LOG_PEPPER" in update
    assert "--update-secrets=SCHWAB_CLIENT_SECRET=schwab-client-secret:latest" in update


def test_requires_schwab_secret(run_setup):
    result, calls, _ = run_setup(SCHWAB_CLIENT_SECRET="")
    assert result.returncode != 0
    assert not any(c.startswith("secrets") for c in calls)
