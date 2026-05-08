"""
Unit tests for SupabaseApplicatorAgent.

Tests dry-run, full apply, backup creation, file overwrite handling, and the
case where the builder hasn't run yet.

Run with: pytest backend/tests/test_applicator_supabase.py -v
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agents.applicator_supabase import SupabaseApplicatorAgent  # noqa: E402
from agents.builder_supabase import SupabaseBuilderAgent  # noqa: E402
from tests.test_builder_supabase import FIXTURE_RECOMMENDATIONS  # noqa: E402


@pytest.fixture
def project_with_build(tmp_path):
    """Real fake project: empty src/ + a Higgsfield-ish file that should NOT be touched."""
    project = tmp_path / "client-site"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "App.tsx").write_text("// Higgsfield-generated entry, do not delete\n")
    (project / "src" / "components").mkdir()
    # Pretend an AdminRoute already exists in the client repo — applicator should back it up.
    (project / "src" / "components" / "AdminRoute.tsx").write_text("// stale version from previous run\n")

    # Run the builder against this project to produce cms-generated/.
    builder = SupabaseBuilderAgent(
        project_path=str(project),
        project_name="client-site",
        analyzer_output={"cms_recommendations": FIXTURE_RECOMMENDATIONS},
    )
    builder_result = asyncio.run(builder.execute())
    assert builder_result["build_status"] == "completed"
    return project, builder_result


def test_dry_run_no_files_copied(project_with_build):
    project, builder_result = project_with_build
    agent = SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output=builder_result,
        auto_apply=False,
    )
    result = asyncio.run(agent.execute())

    assert result["apply_status"] == "awaiting_approval"
    assert result["files_applied"] == []
    # AdminRoute.tsx still has the stale content (we didn't overwrite).
    stale = (project / "src" / "components" / "AdminRoute.tsx").read_text()
    assert "stale version" in stale
    # Plan still lists what would happen.
    assert len(result["files_to_apply"]) > 0


def test_full_apply_copies_files(project_with_build):
    project, builder_result = project_with_build
    agent = SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output=builder_result,
        auto_apply=True,
    )
    result = asyncio.run(agent.execute())

    assert result["apply_status"] == "completed", result.get("errors")
    # Stale file replaced.
    new = (project / "src" / "components" / "AdminRoute.tsx").read_text()
    assert "stale version" not in new
    assert "AdminRoute" in new and "is_admin" in new

    # New files written.
    assert (project / "src" / "components" / "AdminLayout.tsx").exists()
    assert (project / "src" / "components" / "AdminNav.tsx").exists()
    assert (project / "src" / "lib" / "supabase.ts").exists()
    assert (project / "src" / "pages" / "admin" / "ManageServices.tsx").exists()
    assert (project / "src" / "pages" / "admin" / "ManageLocations.tsx").exists()
    assert (project / "src" / "pages" / "admin" / "ManageCoaches.tsx").exists()
    assert (project / "src" / "admin-nav-items.ts").exists()


def test_full_apply_does_not_touch_pre_existing_app_tsx(project_with_build):
    """The Higgsfield-generated App.tsx must survive — we don't overwrite it."""
    project, builder_result = project_with_build
    agent = SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output=builder_result,
        auto_apply=True,
    )
    asyncio.run(agent.execute())

    app = (project / "src" / "App.tsx").read_text()
    assert "Higgsfield-generated entry" in app


def test_full_apply_creates_backup_for_overwritten_files(project_with_build):
    project, builder_result = project_with_build
    agent = SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output=builder_result,
        auto_apply=True,
    )
    result = asyncio.run(agent.execute())

    assert result["backup_location"] is not None
    backup_dir = Path(result["backup_location"])
    assert backup_dir.exists()
    # Backup of the stale AdminRoute should be there.
    backed_up = backup_dir / "src" / "components" / "AdminRoute.tsx"
    assert backed_up.exists()
    assert "stale version" in backed_up.read_text()
    # Manifest written.
    manifest = json.loads((backup_dir / "manifest.json").read_text())
    assert "src/components/AdminRoute.tsx" in manifest["files"]


def test_no_overwrites_no_backup(tmp_path):
    """If the client repo has no overlapping files, no backup directory should be created."""
    project = tmp_path / "client-site"
    project.mkdir()
    (project / "src").mkdir()
    # No AdminRoute.tsx, no Manage*, nothing — fresh project.

    builder = SupabaseBuilderAgent(
        project_path=str(project),
        project_name="client-site",
        analyzer_output={"cms_recommendations": FIXTURE_RECOMMENDATIONS},
    )
    builder_result = asyncio.run(builder.execute())

    agent = SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output=builder_result,
        auto_apply=True,
    )
    result = asyncio.run(agent.execute())

    assert result["apply_status"] == "completed", result.get("errors")
    assert result["backup_location"] is None
    assert not (project / SupabaseApplicatorAgent.BACKUP_ROOT_NAME).exists()


def test_failure_when_builder_output_missing(tmp_path):
    project = tmp_path / "client-site"
    project.mkdir()
    agent = SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output={"output_directory": str(tmp_path / "does-not-exist")},
        auto_apply=True,
    )
    result = asyncio.run(agent.execute())
    assert result["apply_status"] == "failed"
    assert any("not found" in e for e in result["errors"])


def test_failure_when_builder_didnt_produce_src(tmp_path):
    """If cms-generated/ exists but has no src/ — old Kirby builder output."""
    project = tmp_path / "client-site"
    project.mkdir()
    fake_kirby_out = project / "kirby-cms-generated"
    fake_kirby_out.mkdir()
    (fake_kirby_out / "site").mkdir()

    agent = SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output={"output_directory": str(fake_kirby_out)},
        auto_apply=True,
    )
    result = asyncio.run(agent.execute())
    assert result["apply_status"] == "failed"
    assert any("src/" in e for e in result["errors"])


def test_next_steps_always_emitted(project_with_build):
    """Both dry-run and full-apply should produce next_steps for the user."""
    project, builder_result = project_with_build

    dry = asyncio.run(SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output=builder_result,
        auto_apply=False,
    ).execute())
    assert len(dry["next_steps"]) >= 4

    real = asyncio.run(SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output=builder_result,
        auto_apply=True,
    ).execute())
    assert len(real["next_steps"]) >= 4


def test_test_status_gate(project_with_build):
    """If tester says the build is broken, applicator must skip."""
    project, builder_result = project_with_build
    agent = SupabaseApplicatorAgent(
        project_path=str(project),
        project_name="client-site",
        builder_output=builder_result,
        tester_output={"test_status": "failed"},
        auto_apply=True,
    )
    result = asyncio.run(agent.execute())
    assert result["apply_status"] == "skipped"
    assert any("did not pass" in e for e in result["errors"])
