from dataclasses import dataclass

from app.models import ScheduleMonthStatus, ScheduleVersion


@dataclass(frozen=True)
class ScheduleVersionPolicy:
    version: ScheduleVersion | None

    @property
    def status(self) -> str | None:
        return self.version.status if self.version is not None else None

    def can_edit(self) -> bool:
        return self.status == ScheduleMonthStatus.DRAFT.value

    def can_generate(self) -> bool:
        return self.status == ScheduleMonthStatus.DRAFT.value

    def can_regenerate(self) -> bool:
        return self.status in {
            ScheduleMonthStatus.DRAFT.value,
            ScheduleMonthStatus.VALIDATED.value,
        }

    def can_validate(self) -> bool:
        return self.status == ScheduleMonthStatus.DRAFT.value

    def can_revoke_validation(self) -> bool:
        return self.status == ScheduleMonthStatus.VALIDATED.value

    def can_publish(self) -> bool:
        return self.status == ScheduleMonthStatus.VALIDATED.value

    def can_close(self) -> bool:
        return self.status == ScheduleMonthStatus.PUBLISHED.value

    def can_create_correction(self) -> bool:
        return self.status == ScheduleMonthStatus.CLOSED.value

    def can_schedule_ff(self) -> bool:
        return self.can_edit()

    def can_schedule_fc(self) -> bool:
        return self.can_edit()

    def can_schedule_fr(self) -> bool:
        return self.can_edit()

    def can_run_diagnostic(self) -> bool:
        return self.version is not None

    def can_export(self) -> bool:
        return self.status in {
            ScheduleMonthStatus.DRAFT.value,
            ScheduleMonthStatus.VALIDATED.value,
            ScheduleMonthStatus.PUBLISHED.value,
            ScheduleMonthStatus.CLOSED.value,
        }

    def as_dict(self) -> dict[str, bool]:
        return {
            "edit": self.can_edit(),
            "generate": self.can_generate(),
            "regenerate": self.can_regenerate(),
            "validate": self.can_validate(),
            "revoke_validation": self.can_revoke_validation(),
            "publish": self.can_publish(),
            "close": self.can_close(),
            "create_correction": self.can_create_correction(),
            "schedule_ff": self.can_schedule_ff(),
            "schedule_fc": self.can_schedule_fc(),
            "schedule_fr": self.can_schedule_fr(),
            "run_diagnostic": self.can_run_diagnostic(),
            "export": self.can_export(),
        }
