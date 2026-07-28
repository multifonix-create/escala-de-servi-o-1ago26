from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import func

from app.extensions import db
from app.models import FunctionalType, Military, MilitaryTeamHistory, Team
from app.services.backup_service import BackupResult, create_database_backup


CSV_HEADERS = (
    "nim",
    "nome",
    "tipo_funcional",
    "equipa",
    "ativo",
    "data_inicio",
    "data_fim",
    "apto_cr",
    "notas",
)


class OperationalImportError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass(frozen=True)
class ImportRowResult:
    row_number: int
    nim: str
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    existing: bool = False


@dataclass(frozen=True)
class ImportPreview:
    path: Path
    total_rows: int
    rows: list[ImportRowResult]
    blockers: list[str]
    warnings: list[str]

    @property
    def valid_rows(self) -> int:
        return sum(1 for row in self.rows if not row.errors)

    @property
    def invalid_rows(self) -> int:
        return sum(1 for row in self.rows if row.errors)

    @property
    def existing_rows(self) -> int:
        return sum(1 for row in self.rows if row.existing)

    @property
    def duplicate_rows(self) -> int:
        return sum(1 for blocker in self.blockers if "duplicado no ficheiro" in blocker)

    @property
    def can_import(self) -> bool:
        return not self.blockers and self.total_rows > 0


@dataclass(frozen=True)
class ImportReport:
    preview: ImportPreview
    created: int
    updated: int
    ignored: int
    rejected: int
    backup: BackupResult
    final_totals: dict[str, int]
    distribution: dict[str, int]


def preview_military_import(path_value: str | Path) -> ImportPreview:
    path = Path(path_value).expanduser().resolve()
    rows = _read_rows(path)
    blockers: list[str] = []
    warnings: list[str] = []
    seen_nims: set[str] = set()
    results: list[ImportRowResult] = []

    teams_by_code = {team.code: team for team in Team.query.order_by(Team.code.asc()).all()}
    existing_by_nim = {military.nim: military for military in Military.query.all()}

    for index, raw in enumerate(rows, start=2):
        row_errors: list[str] = []
        row_warnings: list[str] = []
        changes: list[str] = []
        nim = _clean(raw.get("nim"))
        name = _clean(raw.get("nome"))
        functional_type = _clean(raw.get("tipo_funcional")).upper()
        team_code = _clean(raw.get("equipa")).upper()
        active = _parse_bool(raw.get("ativo"), row_errors, "ativo")
        start_date = _parse_date(raw.get("data_inicio"), row_errors, "data_inicio")
        end_date = _parse_optional_date(raw.get("data_fim"), row_errors, "data_fim")

        if not nim:
            row_errors.append("NIM obrigatorio.")
        elif nim in seen_nims:
            row_errors.append("NIM duplicado no ficheiro.")
            blockers.append(f"Linha {index}: NIM duplicado no ficheiro ({nim}).")
        seen_nims.add(nim)

        if not name:
            row_errors.append("Nome obrigatorio.")
        if functional_type not in {item.value for item in FunctionalType}:
            row_errors.append("Tipo funcional invalido.")
        if start_date and end_date and end_date < start_date:
            row_errors.append("Data de fim anterior a data de inicio.")
        if _clean(raw.get("apto_cr")):
            row_warnings.append("Campo apto_cr lido mas ainda sem modelo operacional; valor ignorado.")

        team = teams_by_code.get(team_code) if team_code else None
        if functional_type == FunctionalType.PATRULHEIRO.value and active is not False:
            if not team_code:
                row_errors.append("Patrulheiro ativo exige equipa A-E.")
            elif team is None:
                row_errors.append("Equipa invalida; apenas A, B, C, D ou E.")
        elif team_code and functional_type != FunctionalType.PATRULHEIRO.value:
            row_errors.append("Apenas PATRULHEIRO pode ter equipa operacional.")

        existing = existing_by_nim.get(nim)
        if existing:
            _collect_changes(existing, raw, team, changes)
        elif not row_errors:
            changes.append("Criar militar.")

        if row_errors:
            blockers.extend(f"Linha {index}: {error}" for error in row_errors)

        results.append(
            ImportRowResult(
                row_number=index,
                nim=nim,
                status="invalid" if row_errors else ("update" if changes and existing else "create" if not existing else "ignore"),
                errors=row_errors,
                warnings=row_warnings,
                changes=changes,
                existing=existing is not None,
            )
        )
        warnings.extend(f"Linha {index}: {warning}" for warning in row_warnings)

    if not rows:
        blockers.append("O ficheiro nao contem linhas de dados.")

    return ImportPreview(
        path=path,
        total_rows=len(rows),
        rows=results,
        blockers=blockers,
        warnings=warnings,
    )


def import_military_data(path_value: str | Path, confirm: bool = False) -> ImportReport:
    preview = preview_military_import(path_value)
    if not confirm:
        raise OperationalImportError("Importacao nao confirmada; execute apenas pre-visualizacao.", preview.blockers)
    if not preview.can_import:
        raise OperationalImportError("Importacao bloqueada pela pre-visualizacao.", preview.blockers)

    backup = create_database_backup("v19_military_import")
    rows = _read_rows(preview.path)
    teams_by_code = {team.code: team for team in Team.query.order_by(Team.code.asc()).all()}
    created = updated = ignored = 0
    try:
        for raw in rows:
            nim = _clean(raw.get("nim"))
            military = Military.query.filter_by(nim=nim).one_or_none()
            team = teams_by_code.get(_clean(raw.get("equipa")).upper())
            data = _military_data(raw)
            if military is None:
                military = Military(**data)
                db.session.add(military)
                db.session.flush()
                created += 1
            else:
                changed = False
                for field_name, value in data.items():
                    if getattr(military, field_name) != value:
                        setattr(military, field_name, value)
                        changed = True
                updated += 1 if changed else 0
                ignored += 0 if changed else 1
            if team and military.functional_type == FunctionalType.PATRULHEIRO.value:
                _ensure_current_membership(military, team, military.start_date)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return ImportReport(
        preview=preview,
        created=created,
        updated=updated,
        ignored=ignored,
        rejected=preview.invalid_rows,
        backup=backup,
        final_totals=_final_totals(),
        distribution=_distribution(),
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise OperationalImportError(f"Ficheiro CSV inexistente: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = tuple(reader.fieldnames or ())
        if headers != CSV_HEADERS:
            raise OperationalImportError(
                "Cabecalho CSV invalido.",
                [f"Esperado: {', '.join(CSV_HEADERS)}"],
            )
        return [dict(row) for row in reader]


def _military_data(raw: dict[str, str]) -> dict:
    return {
        "nim": _clean(raw.get("nim")),
        "name": _clean(raw.get("nome")),
        "functional_type": _clean(raw.get("tipo_funcional")).upper(),
        "is_active": _parse_bool(raw.get("ativo"), [], "ativo"),
        "start_date": date.fromisoformat(_clean(raw.get("data_inicio"))),
        "end_date": _parse_optional_date(raw.get("data_fim"), [], "data_fim"),
        "notes": _clean(raw.get("notas")) or None,
    }


def _ensure_current_membership(military: Military, team: Team, start_date: date) -> None:
    current = next(
        (membership for membership in military.team_memberships if membership.end_date is None),
        None,
    )
    if current and current.team_id == team.id:
        return
    if current and current.start_date < start_date:
        current.end_date = start_date - timedelta(days=1)
    elif current and current.start_date >= start_date:
        current.team_id = team.id
        current.start_date = start_date
        current.reason = "Importacao operacional v1.9."
        return
    db.session.add(
        MilitaryTeamHistory(
            military_id=military.id,
            team_id=team.id,
            start_date=start_date,
            reason="Importacao operacional v1.9.",
        )
    )


def _collect_changes(existing: Military, raw: dict[str, str], team: Team | None, changes: list[str]) -> None:
    data = _military_data(raw) if _clean(raw.get("data_inicio")) else {}
    for field_name, value in data.items():
        if getattr(existing, field_name) != value:
            changes.append(f"Atualizar {field_name}.")
    if team and (existing.current_team is None or existing.current_team.id != team.id):
        changes.append("Atualizar equipa atual.")


def _final_totals() -> dict[str, int]:
    total = db.session.scalar(db.select(func.count(Military.id))) or 0
    active = db.session.scalar(db.select(func.count(Military.id)).where(Military.is_active.is_(True))) or 0
    return {"total": total, "active": active, "inactive": total - active}


def _distribution() -> dict[str, int]:
    values = {}
    for functional_type in FunctionalType:
        values[functional_type.value] = (
            db.session.scalar(
                db.select(func.count(Military.id)).where(Military.functional_type == functional_type.value)
            )
            or 0
        )
    return values


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _parse_bool(value: str | None, errors: list[str], field_name: str) -> bool:
    normalized = _clean(value).lower()
    if normalized in {"1", "true", "sim", "s", "yes", "y"}:
        return True
    if normalized in {"0", "false", "nao", "n", "no"}:
        return False
    errors.append(f"{field_name} deve ser sim/nao.")
    return False


def _parse_date(value: str | None, errors: list[str], field_name: str) -> date | None:
    normalized = _clean(value)
    if not normalized:
        errors.append(f"{field_name} obrigatoria.")
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        errors.append(f"{field_name} deve usar formato YYYY-MM-DD.")
        return None


def _parse_optional_date(value: str | None, errors: list[str], field_name: str) -> date | None:
    normalized = _clean(value)
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        errors.append(f"{field_name} deve usar formato YYYY-MM-DD.")
        return None
