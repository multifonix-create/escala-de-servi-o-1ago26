from datetime import date, time

from app.extensions import db
from app.models import Assignment, FunctionalType
from app.services.diagnostic_service import ScheduleDiagnosticService
from app.services.schedule_generator import PTGenerationOptions, ScheduleGenerator
from tests.test_pt_generation import _military, _month, _patrols


def _codes(problems):
    return {problem.code for problem in problems}


def test_diagnostic_reports_manual_pt_without_time_or_duration(app):
    with app.app_context():
        _, version = _month()
        military = _military(1)
        db.session.add(
            Assignment(
                schedule_version_id=version.id,
                military_id=military.id,
                assignment_date=date(2026, 1, 1),
                code="PT",
                source="MANUAL",
                is_manual=True,
                is_locked=True,
            )
        )
        db.session.commit()

        problems, summary = ScheduleDiagnosticService().analyze(version)

        assert "PT-MANUAL-MISSING-TIME" in _codes(problems)
        assert "PT-MANUAL-MISSING-DURATION" in _codes(problems)
        assert summary.total_warnings >= 2


def test_diagnostic_reports_pt_assigned_to_cmd_as_error(app):
    with app.app_context():
        _, version = _month()
        cmd = _military(1, FunctionalType.CMD.value)
        db.session.add(
            Assignment(
                schedule_version_id=version.id,
                military_id=cmd.id,
                assignment_date=date(2026, 1, 1),
                code="PT",
                source="SYSTEM",
                is_manual=False,
                is_locked=False,
                start_time=time(8, 0),
                end_time=time(16, 0),
                duration_minutes=480,
            )
        )
        db.session.commit()

        problems, summary = ScheduleDiagnosticService().analyze(version)

        assert "PT-CMD" in _codes(problems)
        assert summary.total_errors >= 1


def test_pt_absence_is_information_and_not_mandatory_coverage(app):
    with app.app_context():
        _, version = _month()
        _patrols(9)

        ScheduleGenerator().generate_at_po(version, PTGenerationOptions(enabled=False))
        problems, summary = ScheduleDiagnosticService().analyze(version)

        assert "PT-NOT-REQUESTED" in _codes(problems)
        assert not any(problem.code == "COVERAGE-MISSING" and problem.details.get("code") == "PT" for problem in problems)
        assert not any(problem.code.startswith("PT-") and problem.level == "ERROR" for problem in problems)
