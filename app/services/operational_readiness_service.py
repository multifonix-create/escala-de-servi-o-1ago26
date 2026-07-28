from dataclasses import dataclass, field
from datetime import date

from app.models import (
    FunctionalType,
    Military,
    MilitaryRestriction,
    MilitaryTeamHistory,
    ScheduleVersion,
    Team,
    TeamCycleReference,
    Unavailability,
)
from app.services.cycle_calculator import preview_team_cycle


READINESS_NOT_READY = "Nao preparado"
READINESS_READY_WITH_WARNINGS = "Preparado com avisos"
READINESS_READY = "Preparado para gerar"


@dataclass(frozen=True)
class ReadinessIssue:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class ReadinessReport:
    status: str
    issues: list[ReadinessIssue]
    counts: dict[str, int]
    distribution: dict[str, int]
    test_versions: list[ScheduleVersion] = field(default_factory=list)

    @property
    def errors(self) -> list[ReadinessIssue]:
        return [issue for issue in self.issues if issue.level == "ERROR"]

    @property
    def warnings(self) -> list[ReadinessIssue]:
        return [issue for issue in self.issues if issue.level == "WARNING"]


def evaluate_operational_readiness(today: date | None = None) -> ReadinessReport:
    today = today or date.today()
    militaries = Military.query.order_by(Military.name.asc(), Military.nim.asc()).all()
    teams = Team.query.order_by(Team.code.asc()).all()
    references = TeamCycleReference.query.order_by(TeamCycleReference.team_id.asc(), TeamCycleReference.valid_from.asc()).all()
    memberships = MilitaryTeamHistory.query.order_by(MilitaryTeamHistory.military_id.asc(), MilitaryTeamHistory.start_date.asc()).all()
    restrictions = MilitaryRestriction.query.all()
    unavailabilities = Unavailability.query.all()
    issues: list[ReadinessIssue] = []

    active = [military for military in militaries if military.is_active]
    patrols = [military for military in active if military.functional_type == FunctionalType.PATRULHEIRO.value]
    if not militaries:
        issues.append(ReadinessIssue("ERROR", "NO-MILITARIES", "Nao existem militares carregados."))
    if not patrols:
        issues.append(ReadinessIssue("ERROR", "NO-ACTIVE-PATROLS", "Nao existem patrulheiros ativos."))

    team_ids_with_patrols = set()
    for military in patrols:
        current = _current_membership(military)
        if current is None:
            issues.append(ReadinessIssue("ERROR", "PATROL-WITHOUT-TEAM", f"Patrulheiro ativo sem equipa atual: NIM {military.nim}."))
            continue
        team_ids_with_patrols.add(current.team_id)

    for military in active:
        if military.functional_type != FunctionalType.PATRULHEIRO.value and _current_membership(military):
            issues.append(ReadinessIssue("ERROR", "NON-PATROL-WITH-TEAM", f"Militar nao patrulheiro com equipa: NIM {military.nim}."))

    for team_id in sorted(team_ids_with_patrols):
        valid_refs = [ref for ref in references if ref.team_id == team_id and ref.is_valid_on(today)]
        if not valid_refs:
            team = next((item for item in teams if item.id == team_id), None)
            code = team.code if team else str(team_id)
            issues.append(ReadinessIssue("ERROR", "TEAM-WITHOUT-CURRENT-REFERENCE", f"Equipa {code} sem referencia de ciclo valida hoje."))

    for issue in _overlap_issues("MEMBERSHIP-OVERLAP", memberships, "military_id", "Historico de equipa sobreposto"):
        issues.append(issue)
    for issue in _overlap_issues("REFERENCE-OVERLAP", references, "team_id", "Referencias de ciclo sobrepostas"):
        issues.append(issue)

    if len(teams) != 5:
        issues.append(ReadinessIssue("WARNING", "TEAM-COUNT", "As equipas oficiais A-E devem estar configuradas."))
    if not restrictions:
        issues.append(ReadinessIssue("WARNING", "NO-RESTRICTIONS", "Nao existem restricoes individuais registadas."))
    if not unavailabilities:
        issues.append(ReadinessIssue("WARNING", "NO-UNAVAILABILITIES", "Nao existem indisponibilidades registadas."))

    counts = {
        "militaries": len(militaries),
        "active_militaries": len(active),
        "teams": len(teams),
        "cycle_references": len(references),
        "restrictions": len(restrictions),
        "unavailabilities": len(unavailabilities),
    }
    distribution = {
        functional_type.value: sum(1 for military in active if military.functional_type == functional_type.value)
        for functional_type in FunctionalType
    }
    status = READINESS_READY
    if any(issue.level == "ERROR" for issue in issues):
        status = READINESS_NOT_READY
    elif any(issue.level == "WARNING" for issue in issues):
        status = READINESS_READY_WITH_WARNINGS

    return ReadinessReport(
        status=status,
        issues=issues,
        counts=counts,
        distribution=distribution,
        test_versions=ScheduleVersion.query.filter_by(is_operational_test=True).order_by(ScheduleVersion.created_at.desc()).limit(10).all(),
    )


def build_cycle_conference(team: Team, start_date: date, end_date: date):
    return preview_team_cycle(team, start_date, end_date)


def _current_membership(military: Military) -> MilitaryTeamHistory | None:
    return next(
        (membership for membership in military.team_memberships if membership.end_date is None),
        None,
    )


def _overlap_issues(code: str, items: list, group_attr: str, message: str) -> list[ReadinessIssue]:
    issues = []
    by_group: dict[int, list] = {}
    for item in items:
        by_group.setdefault(getattr(item, group_attr), []).append(item)
    for group_id, grouped in by_group.items():
        ordered = sorted(grouped, key=lambda item: item.start_date if hasattr(item, "start_date") else item.valid_from)
        for previous, current in zip(ordered, ordered[1:]):
            previous_end = getattr(previous, "end_date", None)
            previous_end = previous_end if previous_end is not None else getattr(previous, "valid_until", None)
            current_start = getattr(current, "start_date", None) or getattr(current, "valid_from")
            if current_start <= (previous_end or date.max):
                issues.append(ReadinessIssue("ERROR", code, f"{message}: grupo {group_id}."))
    return issues
