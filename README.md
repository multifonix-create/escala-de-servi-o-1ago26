# Escala de Serviço

Aplicação local Flask para gestão progressiva da Escala de Serviço.

## Versão atual

v1.7 - Exportacao Operacional da Escala para Excel

Esta versão inclui a infraestrutura inicial, a gestão segura de militares, equipas oficiais A-E, histórico de pertença, referências do ciclo de folgas, restrições individuais, indisponibilidades dos militares, consulta mensal da grelha, edição manual controlada das células, diagnóstico inicial, geração automática AT/PO, regeneração segura de automáticos numa nova versão, otimizações de desempenho, geração automática opcional de PT, gestão funcional inicial de FF por trabalho em feriado, gestão funcional de FC e folgas reagendadas FR e exportacao operacional para Excel.

## Requisitos

- Python 3.11 ou superior
- SQLite

## Instalar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Inicializar migracoes

```powershell
$env:FLASK_APP = "run.py"
flask db init
```

Este comando só é necessário quando a pasta `migrations/` ainda não existe.

## Aplicar migrações

```powershell
$env:FLASK_APP = "run.py"
flask db upgrade
```

## Iniciar

```powershell
$env:FLASK_APP = "run.py"
flask run --host 127.0.0.1 --port 5001
```

Tambem pode ser executada com:

```powershell
python run.py
```

A aplicação fica disponível em:

```text
http://127.0.0.1:5001/
```

Rotas principais:

```text
/
/health
/militares
/militares/novo
/equipas
/ciclo
/ciclo/configurar
/ciclo/pre-visualizar
/restricoes
/indisponibilidades
/escala
/escala/<year>/<month>
/escala/<year>/<month>/versoes
/escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>
/escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>/historico
/escala/<year>/<month>/versoes/<version_id>/diagnostico
/escala/<year>/<month>/versoes/<version_id>/diagnostico/<run_id>
/escala/<year>/<month>/versoes/<version_id>/gerar
/escala/<year>/<month>/versoes/<version_id>/geracoes
/escala/<year>/<month>/versoes/<version_id>/geracoes/<run_id>
/escala/<year>/<month>/versoes/<version_id>/regenerar
/escala/<year>/<month>/versoes/<version_id>/comparar/<other_version_id>
/escala/<year>/<month>/versoes/<version_id>/validar
/escala/<year>/<month>/versoes/<version_id>/revogar-validacao
/escala/<year>/<month>/versoes/<version_id>/publicar
/escala/<year>/<month>/versoes/<version_id>/encerrar
/escala/<year>/<month>/versoes/<version_id>/criar-correcao
/escala/<year>/<month>/versoes/<version_id>/historico-estado
/escala/<year>/<month>/versoes/<version_id>/exportar/excel
/escala/<year>/<month>/versoes/<version_id>/ff/processar
/escala/<year>/<month>/versoes/<version_id>/compensacoes/processar
/feriados
/feriados/novo
/ff
/ff/<credit_id>
/ff/<credit_id>/agendar
/ff/<credit_id>/reagendar
/ff/<credit_id>/historico
/fc
/fc/novo
/fc/<credit_id>
/fc/<credit_id>/agendar
/fc/<credit_id>/reagendar
/fc/<credit_id>/historico
/folgas-reagendadas
/folgas-reagendadas/<credit_id>
/folgas-reagendadas/<credit_id>/agendar
/folgas-reagendadas/<credit_id>/reagendar
/folgas-reagendadas/<credit_id>/historico
/equipas/<id>/ciclo
/equipas/<id>/ciclo/nova-referencia
/equipas/<id>/ciclo/historico
/militares/<id>/equipa
/militares/<id>/equipa/mudar
/militares/<id>/historico-equipas
/militares/<id>/restricoes
/militares/<id>/restricoes/nova
/militares/<id>/restricoes/testar
/militares/<id>/indisponibilidades
/militares/<id>/indisponibilidades/nova
/militares/<id>/indisponibilidades/testar
```

## Testes

```powershell
pytest
```

## Manutencao FC

```powershell
$env:FLASK_APP = "run.py"
flask process-compensations
flask process-compensations --date 2027-01-01
```

## Estado da v1.7

- Equipas oficiais A-E criadas como dados estruturais.
- Referências do ciclo configuráveis manualmente por equipa.
- Cálculo determinístico de fases, DS e DC.
- Restrições individuais configuráveis por militar.
- Tipos de restrição suportados: indisponível, disponível apenas e disponibilidade especial.
- Avaliador central de compatibilidade com datas, dias da semana e janelas horárias.
- Indisponibilidades concretas configuráveis por militar.
- Códigos suportados: LF, LP, BM, LC, LN, DIL, TRIB, INQ, FORMACAO, TIRO e OUTRA.
- Estados suportados: PLANNED, CONFIRMED e CANCELLED.
- Compensação em DS/DC apenas registada, sem criação automática de FF ou FC.
- Meses de escala criáveis manualmente em estado DRAFT.
- Versão inicial criada por mês com origem INITIAL.
- Grelha mensal calculada dinamicamente a partir de militares, histórico de equipas, ciclo, restrições e indisponibilidades.
- Edição manual de células em versões DRAFT.
- Atribuições manuais persistidas com origem MANUAL.
- Histórico de alterações por célula.
- Bloqueio, desbloqueio, limpeza lógica e override explícito.
- Diagnóstico central com níveis ERROR, WARNING e INFO.
- Diagnóstico persistido por execução e problema.
- Diagnóstico de cobertura completo para versões com geração concluída.
- Descanso com horários formalizados para AT1-AT3 e PO1-PO3.
- Geração automática inicial de AT1, AT2, AT3, PO1, PO2 e PO3.
- Geração determinística, sem aleatoriedade.
- Execuções persistidas em `generation_runs`.
- Detalhes de elegibilidade, exclusão e seleção persistidos em `assignment_selection_details`.
- Preservação de todas as atribuições manuais.
- Atribuições automáticas criadas com origem SYSTEM.
- CMD excluído de AT/PO.
- SEC e SI usados apenas quando patrulheiros elegíveis não chegam.
- Falta de cobertura registada como aviso/diagnóstico, sem inventar militares.
- Regeneração segura de automáticos AT/PO numa nova versão.
- Versões regeneradas ligadas à versão de origem.
- Comparação consultiva entre versão de origem e versão resultante.
- Células manuais/importadas preservadas na nova versão.
- Automáticos antigos não são copiados.
- Células limpas continuam sem código ativo.
- Geração, regeneração, grelha e diagnóstico com carregamento em lote.
- Caches locais por execução, sem cache global persistente.
- Testes de regressão de queries em `tests/test_performance.py`.
- PT automático opcional, desligado por defeito.
- PT só é criado depois de AT/PO completo no dia.
- PT não conta para cobertura obrigatória.
- PT exige duração de 6 ou 8 horas, hora inicial e limite diário.
- Campos estruturais de horário/duração em `assignments`.
- PT manual é preservado e conta para o limite diário.
- Regeneração recalcula PT automático e preserva PT manual.
- Diagnóstico inclui regras específicas para PT.
- Feriados configuráveis manualmente, sem registos pré-carregados.
- Créditos FF adquiridos por trabalho em feriado, com origem em atribuição existente.
- O código real no feriado permanece inalterado.
- FF pendente não ocupa célula da escala.
- FF agendada cria célula `FF` manual, bloqueada e ligada ao crédito.
- Reagendamento, cancelamento de agendamento, confirmação de gozo e cancelamento fundamentado do direito.
- Saldo de FF por militar.
- Regeneração segura preserva célula FF manual/importada e a ligação ao mesmo crédito.
- Diagnóstico inclui incoerências FF.
- FC criada por R, CR ou decisao documentada de comando.
- R/CR em dia util gera 1 FC; R/CR ao sabado/domingo gera 2 FC.
- R/CR em feriado nao gera FC e fica elegivel para FF.
- Cada FC e uma unidade independente de 480 minutos.
- FC expira em 31 de dezembro do ano de aquisicao, com protecao quando agendada dentro do prazo.
- FR criada por confirmacao explicita de AT/PO/PT em DS/DC.
- FR nao expira, nao altera o ciclo e nao soma ao saldo FC.
- FC/FR agendadas criam celulas manuais, bloqueadas e ligadas ao direito.
- Regeneracao e versoes de correcao preservam celulas FC/FR manuais/importadas e as ligacoes aos direitos.
- Diagnostico inclui incoerencias e potenciais FC/FR.
- Comando `flask process-compensations` processa expiracoes FC e gozo automatico em versoes oficiais.
- Estados oficiais de versao: NOT_GENERATED, DRAFT, VALIDATED, PUBLISHED e CLOSED.
- Validacao executa sempre novo diagnostico e bloqueia erros criticos.
- Avisos exigem confirmacao explicita para validar.
- Publicacao exige revisao validada atual e mantem apenas uma versao PUBLISHED por mes.
- Encerramento executa diagnostico final e torna a versao imutavel.
- Versoes CLOSED so podem ser corrigidas por nova versao DRAFT de correcao.
- Historico de estado registado em `schedule_version_state_events`.
- Migração v1.6: `9a4e2b7c1d60_add_fc_fr_compensations_v1_6.py`.
- Sem militares fictícios.
- Sem pertenças de equipa fictícias.
- Sem referências fictícias do ciclo.
- Sem restrições fictícias.
- Sem indisponibilidades fictícias.
- Sem escalas fictícias.
- Sem geracao automatica de Ronda ou CR.
- Sem exportacao PDF.
- Sem registo persistente/auditoria funcional de exportacoes.
- Sem correção automática de problemas de diagnóstico.
- Sem autenticação completa.
