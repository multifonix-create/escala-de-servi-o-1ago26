from dataclasses import dataclass


@dataclass(frozen=True)
class AssignmentCodeDefinition:
    code: str
    label: str
    category: str


ASSIGNMENT_CODE_DEFINITIONS = (
    AssignmentCodeDefinition("AT1", "Atendimento 00:00-08:00", "OPERACIONAL"),
    AssignmentCodeDefinition("AT2", "Atendimento 08:00-16:00", "OPERACIONAL"),
    AssignmentCodeDefinition("AT3", "Atendimento 16:00-00:00", "OPERACIONAL"),
    AssignmentCodeDefinition("PO1", "Patrulhamento 00:00-08:00", "OPERACIONAL"),
    AssignmentCodeDefinition("PO2", "Patrulhamento 08:00-16:00", "OPERACIONAL"),
    AssignmentCodeDefinition("PO3", "Patrulhamento 16:00-00:00", "OPERACIONAL"),
    AssignmentCodeDefinition("PT", "Patrulhamento adicional", "OPERACIONAL"),
    AssignmentCodeDefinition("P", "Piquete", "COMANDO"),
    AssignmentCodeDefinition("R", "Ronda", "PENDENTE"),
    AssignmentCodeDefinition("CR", "Compensacao de ronda", "PENDENTE"),
    AssignmentCodeDefinition("FC", "Folga de compensacao", "COMPENSACAO"),
    AssignmentCodeDefinition("FF", "Folga de feriado", "COMPENSACAO"),
    AssignmentCodeDefinition("DS", "Descanso semanal", "DESCANSO"),
    AssignmentCodeDefinition("DC", "Descanso complementar", "DESCANSO"),
    AssignmentCodeDefinition("LF", "Licenca/ferias", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("LP", "Licenca prevista", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("BM", "Baixa medica", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("LC", "Licenca", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("LN", "Licenca", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("DIL", "Diligencia", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("TRIB", "Tribunal", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("INQ", "Inquerito", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("DCP", "Descanso compensatorio pendente", "COMPENSACAO"),
    AssignmentCodeDefinition("D24", "Descanso 24 horas", "DESCANSO"),
    AssignmentCodeDefinition("FORMACAO", "Formacao", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("TIRO", "Tiro", "INDISPONIBILIDADE"),
    AssignmentCodeDefinition("OUTRA", "Outra ausencia", "INDISPONIBILIDADE"),
)

ASSIGNMENT_CODE_CATALOG = {
    definition.code: definition for definition in ASSIGNMENT_CODE_DEFINITIONS
}
ALLOWED_ASSIGNMENT_CODES = tuple(ASSIGNMENT_CODE_CATALOG)
OPERATIONAL_ASSIGNMENT_CODES = {"AT1", "AT2", "AT3", "PO1", "PO2", "PO3", "PT", "P", "R", "CR"}
UNAVAILABILITY_ASSIGNMENT_CODES = {
    "LF",
    "LP",
    "BM",
    "LC",
    "LN",
    "DIL",
    "TRIB",
    "INQ",
    "FORMACAO",
    "TIRO",
    "OUTRA",
}
