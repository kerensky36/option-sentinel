"""Tests for scripts/backend_changed.sh (specs/017 T025).

Exit 0 = backend must be deployed, exit 1 = backend unchanged since the deployed commit.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "backend_changed.sh"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    for d in ("src", "frontend", "specs", "scripts"):
        (tmp_path / d).mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    (tmp_path / "frontend" / "page.html").write_text("<p>hi</p>\n")
    (tmp_path / "specs" / "spec.md").write_text("spec\n")
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    (tmp_path / "Dockerfile").write_text("FROM python\n")
    (tmp_path / "README.md").write_text("readme\n")
    shutil.copy(_SCRIPT, tmp_path / "scripts" / "backend_changed.sh")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return tmp_path


def _commit(repo: Path, msg: str = "c") -> None:
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", msg)


def _changed(repo: Path, deployed: str) -> bool:
    result = subprocess.run(
        ["bash", "scripts/backend_changed.sh", deployed], cwd=repo, capture_output=True, text=True
    )
    assert result.returncode in (0, 1), result.stderr
    return result.returncode == 0


def test_no_deployed_sha_means_deploy(repo):
    assert _changed(repo, "") is True


def test_unknown_sha_means_deploy(repo):
    assert _changed(repo, "deadbeefdead") is True


def test_dirty_deployed_label_means_deploy(repo):
    sha = _git(repo, "rev-parse", "--short=12", "HEAD")
    assert _changed(repo, f"{sha}-dirty") is True


def test_nothing_changed_means_skip(repo):
    sha = _git(repo, "rev-parse", "--short=12", "HEAD")
    assert _changed(repo, sha) is False


def test_docs_only_change_means_skip(repo):
    sha = _git(repo, "rev-parse", "--short=12", "HEAD")
    (repo / "README.md").write_text("new readme\n")
    (repo / "specs" / "spec.md").write_text("new spec\n")
    _commit(repo)
    assert _changed(repo, sha) is False


@pytest.mark.parametrize(
    "path",
    ["src/app.py", "frontend/page.html", "requirements.txt", "Dockerfile"],
)
def test_committed_backend_change_means_deploy(repo, path):
    sha = _git(repo, "rev-parse", "--short=12", "HEAD")
    (repo / path).write_text("changed\n")
    _commit(repo)
    assert _changed(repo, sha) is True


def test_uncommitted_backend_change_means_deploy(repo):
    sha = _git(repo, "rev-parse", "--short=12", "HEAD")
    (repo / "src" / "app.py").write_text("x = 2\n")
    assert _changed(repo, sha) is True


def test_new_untracked_backend_file_means_deploy(repo):
    sha = _git(repo, "rev-parse", "--short=12", "HEAD")
    (repo / "src" / "new_module.py").write_text("y = 1\n")
    assert _changed(repo, sha) is True
