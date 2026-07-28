# Changelog

## v1.8 - 2026-07-28

### Adicionado
- Criada exportacao operacional da escala mensal para PDF A3.
- Adicionado `SchedulePdfExportService` em `app/services/export_service.py`.
- Adicionada rota `GET /escala/<year>/<month>/versoes/<version_id>/exportar/pdf`.
- Adicionado botao `Exportar PDF A3` na grelha mensal, mantendo a exportacao Excel.
- Adicionada dependencia `reportlab==4.2.5`.
- Adicionados testes em `tests/test_pdf_export.py`.

### Regras
- A exportacao PDF reutiliza `MonthlyGridBuilder` e representa a versao selecionada.
- Estados exportaveis: `DRAFT`, `VALIDATED`, `PUBLISHED` e `CLOSED`.
- O PDF inclui grelha mensal A3 landscape, legenda, resumo, diagnostico persistido e alteracoes manuais quando existirem.
- A exportacao nao executa diagnostico, geracao, regeneracao ou manutencao de compensacoes.
- A exportacao nao altera a base de dados, nao persiste ficheiros PDF e nao cria `export_records`.
- Textos exportados recebem protecao contra formula injection e caracteres de controlo.

### Migracao
- Nao foi criada migracao na v1.8.
- A revisao Alembic mantem-se em `9a4e2b7c1d60`.
- Nao foram alteradas migracoes anteriores.

### Testes
- Suite nova v1.8 validada com `4 passed`.
- Suite Excel/PDF validada com `7 passed`.
- Suite completa validada com `250 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real permaneceu intacta.
- Nao foram criados militares, equipas, escalas, atribuicoes, diagnosticos, creditos, ficheiros exportados persistentes ou dados ficticios.

### Limitacoes
- Sem registo persistente/auditoria funcional de exportacoes.
- Sem geracao automatica de Ronda.
- Sem geracao automatica de CR.
- Sem remunerados.
- Sem notificacoes.
- Sem autenticacao completa.

## v1.7 - 2026-07-28

### Adicionado
- Criada exportacao operacional da escala mensal para Excel.
- Adicionado servico central `app/services/export_service.py`.
- Adicionada rota `GET /escala/<year>/<month>/versoes/<version_id>/exportar/excel`.
- Adicionado botao `Exportar Excel` na grelha mensal.
- Adicionada politica `ScheduleVersionPolicy.can_export()`.
- Adicionada dependencia `openpyxl==3.1.5`.
- Adicionados testes em `tests/test_excel_export.py`.

### Regras
- A exportacao reutiliza `MonthlyGridBuilder` e representa a versao selecionada.
- Estados exportaveis: `DRAFT`, `VALIDATED`, `PUBLISHED` e `CLOSED`.
- A exportacao nao executa diagnostico, geracao, regeneracao ou manutencao de compensacoes.
- A exportacao nao altera a base de dados e nao persiste ficheiros XLSX.
- Textos exportados recebem protecao contra formula injection.

### Migraçao
- Nao foi criada migracao na v1.7.
- A revisao Alembic mantem-se em `9a4e2b7c1d60`.
- Nao foram alteradas migracoes anteriores.

### Testes
- Suite nova v1.7 validada com `3 passed`.
- Suite completa validada com `246 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real permaneceu intacta.
- Nao foram criados militares, equipas, escalas, atribuicoes, diagnosticos, creditos, ficheiros exportados persistentes ou dados ficticios.

### Limitacoes
- Sem exportacao PDF.
- Sem registo persistente/auditoria funcional de exportacoes.
- Sem geracao automatica de Ronda.
- Sem geracao automatica de CR.
- Sem remunerados.
- Sem notificacoes.
- Sem autenticacao completa.

## v1.6 - 2026-07-28

### Adicionado
- Criada gestao funcional inicial de `FC` e `FR`.
- Adicionados modelos `CompensatoryLeaveCredit`, `CompensatoryLeaveCreditEvent`, `RescheduledRestCredit` e `RescheduledRestCreditEvent`.
- Adicionados campos `assignments.compensatory_leave_credit_id` e `assignments.rescheduled_rest_credit_id`.
- Criado servico central `app/services/compensation_service.py`.
- Criado blueprint `app/routes/compensations.py`.
- Criadas paginas para listar, criar FC por decisao de comando, detalhar, agendar, reagendar, cancelar e consultar historico de FC.
- Criadas paginas para listar, detalhar, agendar, reagendar, cancelar, confirmar gozo e consultar historico de FR.
- Criado processamento explicito de potenciais FC/FR por versao em `/escala/<year>/<month>/versoes/<version_id>/compensacoes/processar`.
- Criado comando `flask process-compensations` com opcao `--date`.
- Adicionado codigo `FR` ao catalogo de atribuicoes.
- Atualizada elegibilidade FF para incluir `R` e `CR` em feriado.
- Integrado diagnostico inicial de FC/FR.
- Integrada preservacao de ligacoes FC/FR em regeneracao e versoes de correcao.

### Regras
- `FF`, `FC` e `FR` permanecem conceitos separados.
- `FC` nasce de `R`, `CR` ou decisao documentada de comando.
- `R` e `CR` em dia util geram 1 FC; ao sabado/domingo geram 2 FC; em feriado nao geram FC.
- Cada FC e uma unidade indivisivel de 480 minutos.
- `FR` nasce apenas de `AT1-AT3`, `PO1-PO3` ou `PT` em `DS`/`DC`.
- `FR` nao expira, nao soma ao saldo FC e nao altera o ciclo DS/DC.
- Agendamento de `FC`/`FR` cria celula manual, bloqueada e ligada ao direito.
- O editor generico nao cria, limpa, desbloqueia ou altera celulas `FF`, `FC` ou `FR` ligadas.
- Versoes nao `DRAFT` nao recebem novos agendamentos de `FC`/`FR`.
- Expiracao e gozo automatico de FC sao processados por manutencao idempotente, sem mutacoes no arranque.

### Migracao
- Criada e aplicada a migracao `9a4e2b7c1d60_add_fc_fr_compensations_v1_6.py`.
- Nao foram alteradas migracoes anteriores.
- Backup previo da base real: `instance/backups/escala_20260728_175202_v16_pre_migration.db`.
- A migracao criou apenas estrutura; nao criou creditos, eventos, atribuicoes, versoes ou dados operacionais.

### Testes
- Adicionados testes em `tests/test_compensations.py`.
- Suite nova v1.6 validada com `14 passed`.
- Suite completa validada com `243 passed`.
- `compileall` executado com sucesso.

### Base de dados
- Revisao Alembic atual: `9a4e2b7c1d60`.
- A base real ficou com `0` militares.
- A base real ficou com `0` escalas, versoes e atribuicoes.
- A base real ficou com `0` FF, FC e FR.
- Nao foram criados dados ficticios ou demonstrativos.

### Limitacoes
- Sem geracao automatica de Ronda.
- Sem geracao automatica de CR.
- Sem remunerados.
- Sem notificacoes.
- Sem exportacoes operacionais.
- Sem autenticacao completa.

## v1.5 - 2026-07-28

### Adicionado
- Criado workflow de estado das versoes da escala: `DRAFT`, `VALIDATED`, `PUBLISHED` e `CLOSED`.
- Adicionados campos de revisao, validacao, publicacao e encerramento em `schedule_versions`.
- Adicionado ponteiro `schedule_months.published_version_id` para a versao oficial do mes.
- Criada tabela `schedule_version_state_events`.
- Criado servico central `app/services/schedule_version_workflow.py`.
- Criada politica central `app/services/schedule_version_policy.py`.
- Criadas rotas e paginas para validar, revogar validacao, publicar, encerrar, criar versao de correcao e consultar historico de estado.
- Adicionado diagnostico de incoerencias do workflow de estado.
- Integrada revisao de conteudo em edicao manual, geracao automatica, regeneracao e FF.

### Regras
- Validacao executa sempre novo diagnostico.
- Erros bloqueantes impedem validacao, publicacao e encerramento.
- Avisos exigem confirmacao explicita para validar.
- Publicacao exige validacao atual e revisao sem alteracoes posteriores.
- Apenas uma versao pode ficar `PUBLISHED` por mes.
- Publicar uma nova versao faz a anterior publicada regressar a `VALIDATED`.
- Versoes `CLOSED` sao imutaveis.
- Correcao de versao fechada cria nova versao `DRAFT`, preservando a versao original.
- A copia de correcao preserva atribuicoes visiveis e ligacoes FF sem duplicar creditos.

### Migracao
- Criada migracao `d34f6a9b8c21_add_schedule_validation_publication_v1_5.py`.
- Nao foram alteradas migracoes anteriores.
- Nao foram inseridos estados, eventos, meses, versoes, atribuicoes ou dados operacionais durante a migracao.
- Backup previo da base real: `instance/backups/escala_20260728_164217_v15_pre_migration.db`.

### Testes
- Adicionados testes de workflow em `tests/test_schedule_workflow.py`.
- Suite v1.5 validada com `6 passed`.
- Suite completa validada com `229 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A migracao adiciona infraestrutura de estado e historico.
- Nao foram criados militares ficticios.
- Nao foram criadas equipas ficticias.
- Nao foram criadas escalas ficticias.
- Nao foram criados dados demonstrativos.

### Limitacoes
- Sem FC funcional.
- Sem Ronda, CR, remunerados, exportacoes, notificacoes ou autenticacao completa.
- Sem correcao automatica de problemas de diagnostico.

## v1.4 - 2026-07-28

### Adicionado
- Criada gestão funcional inicial de `FF` por trabalho em feriado.
- Adicionados modelos `Holiday`, `HolidayLeaveCredit` e `HolidayLeaveCreditEvent`.
- Adicionada ligação explícita `assignments.holiday_leave_credit_id`.
- Criado serviço `app/services/holiday_credit_service.py`.
- Criadas rotas e páginas para feriados, créditos FF, processamento de candidatos, agendamento, reagendamento, cancelamento e confirmação de gozo.
- Adicionado diagnóstico específico de incoerências FF.
- Adicionados testes de integração em `tests/test_holiday_leave.py`.

### Regras
- O dia do feriado mantém o código real executado (`AT1-AT3`, `PO1-PO3` ou `PT`).
- A FF nasce como crédito autónomo e pendente.
- A criação é idempotente por `source_assignment_id`.
- Rascunhos exigem confirmação explícita de serviço prestado.
- A célula `FF` agendada é manual, bloqueada e ligada ao crédito.
- Regeneração segura preserva a ligação ao crédito FF.
- Limpeza ou edição genérica de célula FF ligada a crédito fica bloqueada.
- FF não altera o ciclo `DS/DC`.
- FF não é agendada em `DS/DC` nem sobre indisponibilidade ativa nesta versão.

### Migração
- Criada e aplicada a migração `621f28c3f5b5_add_holiday_leave_credits_v1_4.py`.
- Criadas as tabelas `holidays`, `holiday_leave_credits` e `holiday_leave_credit_events`.
- Adicionado campo opcional `holiday_leave_credit_id` em `assignments`.
- Não foram alteradas migrações anteriores.
- Não foram inseridos feriados, créditos ou eventos FF.
- Backup prévio da base real: `instance/backups/escala_20260728_160219_v14_pre_migration.db`.

### Testes
- Suite nova FF validada com `7 passed`.
- Suite completa validada com `223 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` feriados.
- A base real ficou com `0` créditos FF.
- A base real ficou com `0` eventos FF.
- A base real ficou com `0` meses, versões, atribuições, gerações e diagnósticos.
- Revisão Alembic atual: `621f28c3f5b5`.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem FC funcional.
- Sem Ronda, CR, remunerados ou exportações.
- Sem confirmação operacional diária geral de serviços executados.
- Sem permissões/autenticação completa.

## v1.3 - 2026-07-28

### Adicionado
- Criada geração automática opcional de `PT` depois da cobertura AT/PO.
- Adicionados campos opcionais `start_time`, `end_time` e `duration_minutes` em `assignments`.
- Adicionada seleção determinística específica para PT, com métricas próprias.
- Adicionados detalhes de seleção `PT` em `assignment_selection_details`.
- Adicionados parâmetros PT por execução em `GenerationRun.parameters_json`.
- Adicionado diagnóstico específico de PT.
- Adicionados testes `tests/test_pt_generation.py` e `tests/test_pt_diagnostics.py`.
- Adicionado teste de performance para geração com PT.

### Regras
- PT fica desativado por defeito.
- PT exige ativação explícita, duração de 6 ou 8 horas, hora inicial, limite diário e dias aplicáveis.
- PT só é gerado quando AT/PO do dia está completo.
- PT não conta para a cobertura obrigatória.
- Ausência de PT não é erro.
- CMD nunca recebe PT.
- SEC/SI não recebem PT automático por defeito.
- DS/DC, indisponibilidades, restrições e descanso mínimo continuam a bloquear PT automático.
- PT manual é preservado e conta para o limite diário.

### Regeneração
- PT automático antigo não é copiado.
- PT automático é recalculado na nova versão quando solicitado.
- PT manual é copiado e preserva horário/duração quando existirem.

### Diagnóstico
- `INFO`: PT não solicitado, sem sobrantes ou bloqueado por cobertura AT/PO incompleta.
- `WARNING`: PT manual sem horário/duração, PT manual em DS/DC e excesso sobre limite diário.
- `ERROR`: PT em CMD, PT automático em DS/DC, indisponibilidade confirmada, descanso insuficiente ou intervalo inválido.

### Migração
- Criada e aplicada a migração `adaa03cbb54b_add_pt_assignment_timing_fields.py`.
- A migração adiciona apenas campos opcionais em `assignments` e permite `PT` em `assignment_selection_details`.
- Não foram alteradas migrações anteriores.
- Backup prévio da base real: `instance/backups/escala_20260728_151346_v13_pre_migration.db`.

### Testes
- Suite completa validada com `215 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` meses, versões, atribuições, gerações, detalhes de seleção e diagnósticos.
- Não foram criados PT reais, dados fictícios ou dados demonstrativos.
- Revisão Alembic atual: `adaa03cbb54b`.

### Limitações
- Sem FF, FC, Ronda, CR, remunerados ou exportações.
- Sem configuração global persistente de PT.
- SEC/SI para PT automático exige parâmetro explícito, ainda sem interface dedicada além da política por execução.

## v1.2 - 2026-07-28

### Adicionado
- Criados testes de regressão de desempenho e queries em `tests/test_performance.py`.
- Adicionados caches locais por execução para equipa por militar/data e ciclo por equipa/data.
- Adicionados mapas em memória para pertenças, referências, restrições e indisponibilidades durante geração, grelha e diagnóstico.

### Alterado
- Otimizado `ScheduleGenerator` para evitar queries por candidato/turno.
- Otimizado `CandidateSelector` através de `GenerationContext` pré-carregado.
- Otimizado `ScheduleRegenerationService` por reutilizar o gerador otimizado.
- Otimizado `MonthlyGridBuilder` para evitar queries por célula.
- Otimizado `ScheduleDiagnosticService` para evitar consultas repetidas por atribuição.

### Medições
- Geração 25: `28.581s / 51.232 queries` -> `2.978s / 6.973 queries`.
- Geração 50: `56.994s / 108.080 queries` -> `5.359s / 12.134 queries`.
- Regeneração 50: `58.627s / 108.071 queries` -> `6.638s / 12.149 queries`.
- Grelha 50: `3.991s / 8.132 queries` -> `0.117s / 287 queries`.
- Diagnóstico 50: `0.800s / 1.220 queries` -> `0.082s / 384 queries`.
- Geração 100: `102.909s / 182.353 queries` -> `10.344s / 22.754 queries`.
- Suite completa: `200 passed in 171.65s` -> `203 passed in 53.24s`.

### Migração
- Não foi criada migração na v1.2.
- Não foram adicionados índices novos.
- A revisão Alembic mantém-se em `a999dc4dceba`.
- Não foi necessário backup novo, porque não houve migração.

### Regras
- Não foram alteradas regras operacionais.
- A ordem de seleção foi preservada.
- A explicabilidade e os detalhes de seleção foram preservados.
- Não foi introduzida cache global.

### Testes
- Suite completa validada com `203 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real permaneceu sem militares, versões, atribuições, gerações ou diagnósticos de teste.
- Não foram criados dados fictícios ou demonstrativos.

## v1.1 - 2026-07-28

### Adicionado
- Criada regeneração segura de atribuições automáticas AT/PO numa nova versão.
- Adicionado serviço `app/services/schedule_regeneration.py`.
- Adicionado modo `REGENERATE_AUTOMATIC`.
- Adicionada comparação consultiva entre versão de origem e versão resultante.
- Criadas páginas de confirmação de regeneração e comparação de versões.
- Separadas na interface as ações `Completar celulas vazias` e `Regenerar automaticos`.

### Regras
- A regeneração cria sempre nova `ScheduleVersion`.
- A versão anterior fica preservada.
- A nova versão usa `source=SYSTEM`, estado `DRAFT` e `parent_version_id`.
- Apenas atribuições manuais/importadas visíveis são copiadas.
- Atribuições automáticas antigas não são copiadas.
- Células limpas continuam sem código ativo.
- `DRAFT` e `VALIDATED` podem originar nova versão.
- `PUBLISHED` e `CLOSED` ficam bloqueadas nesta fase.
- O diagnóstico final é executado sobre a nova versão.

### Migração
- Criada e aplicada a migração `a999dc4dceba_add_safe_regeneration_metadata.py`.
- Adicionados campos opcionais `parent_version_id` e `generation_mode` em `schedule_versions`.
- Adicionados campos opcionais `generation_mode`, `source_version_id` e `result_version_id` em `generation_runs`.
- Não foram alteradas migrações anteriores.
- Não foram criadas versões, gerações ou atribuições.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260728_134906_v11_pre_migration.db`.

### Testes
- Adicionados testes de nova versão, relação entre versões, preservação manual, células limpas, automáticos não copiados, estados, rollback, comparação, rotas e caso real prioritário.
- Suite completa validada com `200 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` versões de escala.
- A base real ficou com `0` atribuições.
- A base real ficou com `0` alterações de atribuição.
- A base real ficou com `0` execuções de diagnóstico.
- A base real ficou com `0` problemas de diagnóstico.
- A base real ficou com `0` execuções de geração.
- A base real ficou com `0` detalhes de seleção.
- Revisão Alembic atual: `a999dc4dceba`.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem regeneração destrutiva na mesma versão.
- Sem criação automática de nova versão no modo `FILL_EMPTY`.
- Sem PT, FF, FC, Ronda, CR, remunerados, exportações, publicação automática ou correção automática.

## v1.0 - 2026-07-28

### Adicionado
- Criada geração automática inicial limitada aos serviços `AT1`, `AT2`, `AT3`, `PO1`, `PO2` e `PO3`.
- Adicionados modelos `GenerationRun` e `AssignmentSelectionDetail`.
- Adicionado serviço central `app/services/schedule_generator.py`.
- Adicionados `ScheduleGenerator` e `CandidateSelector`.
- Criadas páginas de confirmação, lista e detalhe das execuções de geração.
- Integrado resumo da última geração na página mensal.
- Integrado marcador `S` na grelha para atribuições geradas pelo sistema.

### Regras
- Mínimos diários: `AT1=1`, `AT2=1`, `AT3=1`, `PO1=2`, `PO2=2`, `PO3=2`.
- Ordem fixa de geração: `AT1`, `PO1`, `AT2`, `PO2`, `AT3`, `PO3`.
- Seleção determinística, sem `random`.
- Período de equidade: mês atual e até três meses anteriores existentes.
- A geração preserva todas as atribuições manuais, bloqueadas ou não.
- A geração cria apenas atribuições `SYSTEM`, `is_manual=False`, `is_locked=False` e `has_override=False`.
- `CMD` nunca recebe AT/PO.
- `SEC` e `SI` só são usados quando não existem patrulheiros elegíveis suficientes.
- DS/DC, indisponibilidades confirmadas e planeadas, restrições e descanso mínimo de oito horas são respeitados.
- Falta de cobertura não cria militares, não duplica militares e não falha tecnicamente; fica explicada.

### Diagnóstico
- Após uma geração concluída, é executado diagnóstico final.
- A cobertura AT/PO passa a ser validada de forma completa para versões com geração concluída.
- O diagnóstico continua a não corrigir automaticamente.

### Migração
- Criada e aplicada a migração `a284728b2308_create_generation_runs_and_selection_.py`.
- Criadas apenas as tabelas `generation_runs` e `assignment_selection_details`.
- Não foram alteradas migrações anteriores.
- Não foram inseridas gerações, seleções ou atribuições.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260728_131456_v10_pre_migration.db`.

### Testes
- Adicionados testes de cobertura AT/PO, preservação manual, exclusão de CMD, uso controlado de SEC/SI, indisponibilidades, restrições, descanso, determinismo, rotas e diagnóstico final.
- Suite completa validada com `191 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` pertenças.
- A base real ficou com `0` referências do ciclo.
- A base real ficou com `0` restrições individuais.
- A base real ficou com `0` indisponibilidades.
- A base real ficou com `0` eventos de indisponibilidade.
- A base real ficou com `0` meses de escala.
- A base real ficou com `0` versões de escala.
- A base real ficou com `0` atribuições.
- A base real ficou com `0` alterações de atribuição.
- A base real ficou com `0` execuções de diagnóstico.
- A base real ficou com `0` problemas de diagnóstico.
- A base real ficou com `0` execuções de geração.
- A base real ficou com `0` detalhes de seleção.
- Revisão Alembic atual: `a284728b2308`.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- A geração atua sobre uma versão `DRAFT` existente e não cria automaticamente nova versão.
- O único modo implementado é completar células vazias.
- Não remove nem regenera automáticos anteriores.
- Sem PT, FF, FC, Ronda, CR, remunerados, exportações, publicação automática, autenticação completa ou correção automática.

## v0.9 - 2026-07-28

### Adicionado
- Criado sistema centralizado de diagnóstico inicial da escala.
- Adicionados modelos `DiagnosticRun` e `DiagnosticIssue`.
- Adicionado serviço `app/services/diagnostic_service.py`.
- Adicionado catálogo `app/services/service_code_catalog.py` com horários formalizados de AT1-AT3 e PO1-PO3.
- Criadas páginas para diagnóstico, reexecução, filtros e detalhe de problema.
- Integrado indicador discreto `D` na grelha para células afetadas pelo último diagnóstico.

### Regras
- Níveis suportados: `ERROR`, `WARNING` e `INFO`.
- Categorias suportadas: `CONFIGURATION`, `MILITARY`, `TEAM`, `CYCLE`, `UNAVAILABILITY`, `RESTRICTION`, `ASSIGNMENT`, `SCHEDULE_STATE`, `COVERAGE`, `REST`, `COMPENSATION` e `SYSTEM`.
- O diagnóstico analisa e explica; não corrige automaticamente.
- Execuções novas preservam execuções anteriores.
- Cobertura é parcial e baseada apenas em atribuições manuais existentes.
- Descanso é parcial e usa apenas horários formalizados.

### Migração
- Criada e aplicada a migração `1a69c7554b89_create_diagnostic_runs_and_issues.py`.
- Criadas apenas as tabelas `diagnostic_runs` e `diagnostic_issues`.
- Não foram alteradas migrações anteriores.
- Não foram inseridos diagnósticos.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260728_125251_v09_pre_migration.db`.

### Testes
- Adicionados testes de execução vazia, persistência, referência de ciclo em falta, serviço em DS, override, indisponibilidade confirmada, descanso curto, rotas e caso real prioritário.
- Suite completa validada com `178 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` pertenças.
- A base real ficou com `0` referências do ciclo.
- A base real ficou com `0` restrições individuais.
- A base real ficou com `0` indisponibilidades.
- A base real ficou com `0` eventos de indisponibilidade.
- A base real ficou com `0` meses de escala.
- A base real ficou com `0` versões de escala.
- A base real ficou com `0` atribuições.
- A base real ficou com `0` alterações de atribuição.
- A base real ficou com `0` execuções de diagnóstico.
- A base real ficou com `0` problemas de diagnóstico.
- Revisão Alembic atual: `1a69c7554b89`.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem geração automática, seleção automática de militares, equidade, cobertura AT/PO real gerada, descanso completo para todos os códigos, FF/FC funcionais, Ronda, CR, remunerados, exportações, autenticação completa e auditoria funcional genérica.

## v0.8 - 2026-07-28

### Adicionado
- Criada edição manual controlada das células da escala.
- Adicionados modelos `Assignment` e `AssignmentChange`.
- Adicionado catálogo central `app/services/assignment_codes.py`.
- Adicionado serviço `app/services/assignment_service.py`.
- Criadas páginas para editar célula e consultar histórico.
- Integrada a atribuição manual persistida no `MonthlyGridBuilder`.

### Regras
- Apenas versões `DRAFT` permitem edição normal.
- Atribuições novas são manuais e ficam bloqueadas por defeito quando selecionado na interface.
- A grelha apresenta primeiro a atribuição manual persistida e preserva o ciclo, indisponibilidade e restrições subjacentes.
- Avisos ultrapassáveis exigem override explícito e motivo.
- BM confirmada bloqueia override normal.
- A limpeza da célula é lógica através de `is_cleared` e preserva o histórico.
- `FF` e `FC` manuais não criam nem consomem créditos.
- `DS` e `DC` manuais não alteram o ciclo.
- Códigos de indisponibilidade manuais não criam indisponibilidades.

### Migração
- Criada e aplicada a migração `465d32473e31_create_assignments_and_assignment_.py`.
- Criadas apenas as tabelas `assignments` e `assignment_changes`.
- Não foram alteradas migrações anteriores.
- Não foram inseridas atribuições ou alterações.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260728_123400_v08_pre_migration.db`.

### Testes
- Adicionados testes de atribuições manuais, unicidade, códigos inválidos, estados, DS/DC, indisponibilidades, BM, override, limpeza, histórico, builder e rotas.
- Suite completa validada com `170 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` pertenças.
- A base real ficou com `0` referências do ciclo.
- A base real ficou com `0` restrições individuais.
- A base real ficou com `0` indisponibilidades.
- A base real ficou com `0` eventos de indisponibilidade.
- A base real ficou com `0` meses de escala.
- A base real ficou com `0` versões de escala.
- A base real ficou com `0` atribuições.
- A base real ficou com `0` alterações de atribuição.
- Revisão Alembic atual: `465d32473e31`.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem geração automática, distribuição AT/PO/PT, equidade, descanso entre serviços, diagnóstico global completo, FF/FC funcionais, Ronda, CR, remunerados, exportações, autenticação completa e auditoria funcional genérica.

## v0.7 - 2026-07-28

### Adicionado
- Criada grelha mensal da escala para consulta controlada.
- Adicionados modelos `ScheduleMonth` e `ScheduleVersion`.
- Adicionado serviço `app/services/schedule_service.py`.
- Adicionado builder central `app/services/monthly_grid_builder.py`.
- Adicionado validador `app/validators/schedule_validator.py`.
- Criadas páginas para seletor mensal, mês vazio, grelha mensal e histórico simples de versões.
- Integrada navegação principal para `/escala`.

### Regras
- A criação de mês é manual e controlada.
- Um mês novo fica em estado `DRAFT`.
- A primeira versão fica com número `1` e origem `INITIAL`.
- A grelha usa militares relevantes para o período, incluindo histórico quando aplicável.
- DS/DC são calculados dinamicamente pelo `CycleCalculator`.
- A pertença à equipa é determinada por dia através do histórico.
- Indisponibilidades canceladas não ocupam a grelha.
- Indisponibilidades confirmadas prevalecem visualmente sobre DS/DC, preservando a informação do ciclo.
- Restrições aparecem como indicadores e não como código principal.
- Feriados permanecem pendentes; `is_holiday` fica sempre `False`.

### Decisões
- Não foi criada tabela de atribuições/células na v0.7.
- A grelha é calculada em leitura a partir das fontes de verdade existentes.
- Não foram implementadas geração AT/PO/PT, distribuição, descanso, FF, FC, Ronda, CR, remunerados, exportações, diagnóstico global ou edição livre.

### Migração
- Criada e aplicada a migração `91f6d17e963f_create_schedule_months_and_versions.py`.
- Criadas apenas as tabelas `schedule_months` e `schedule_versions`.
- Não foram alteradas migrações anteriores.
- Não foram criados meses, versões, células, escalas ou dados fictícios.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260728_115352_v07_pre_migration.db`.

### Testes
- Adicionados testes de validação, serviço, criação controlada, grelha dinâmica, rotas e isolamento.
- Suite completa validada com `158 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` pertenças.
- A base real ficou com `0` referências do ciclo.
- A base real ficou com `0` restrições individuais.
- A base real ficou com `0` indisponibilidades.
- A base real ficou com `0` eventos de indisponibilidade.
- A base real ficou com `0` meses de escala.
- A base real ficou com `0` versões de escala.
- Revisão Alembic atual: `91f6d17e963f`.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem geração de escala, atribuições AT/PO/PT, descanso entre serviços, diagnósticos globais, edição manual, preservação de alterações manuais, FF, FC, Ronda, CR, remunerados, exportações, autenticação completa e auditoria funcional genérica.

## v0.6 - 2026-07-28

### Adicionado
- Criada gestão de indisponibilidades concretas dos militares.
- Adicionados modelos `Unavailability` e `UnavailabilityEvent`.
- Adicionados serviços `app/services/unavailability_service.py`, `app/services/unavailability_evaluator.py` e `app/services/availability_evaluator.py`.
- Criadas páginas para listagem geral, listagem por militar, criação, detalhe, edição, confirmação, cancelamento, reativação e teste manual de compatibilidade.
- Integrado resumo de indisponibilidades na ficha do militar.

### Regras
- Códigos suportados: `LF`, `LP`, `BM`, `LC`, `LN`, `DIL`, `TRIB`, `INQ`, `FORMACAO`, `TIRO` e `OUTRA`.
- Estados suportados: `PLANNED`, `CONFIRMED` e `CANCELLED`.
- Estados de compensação: `NOT_APPLICABLE`, `PENDING_DECISION`, `GENERATES_CREDIT` e `DOES_NOT_GENERATE_CREDIT`.
- Apenas indisponibilidades confirmadas, ativas e não canceladas bloqueiam intervalos de serviço.
- Indisponibilidade confirmada prevalece sobre restrições individuais.
- Dia completo ocupa todos os dias do período.
- Indisponibilidade parcial multi-dia representa um intervalo contínuo entre data/hora inicial e data/hora final.
- Deslocações antes e depois alargam o intervalo efetivo.
- Duplicados exatos são bloqueados; sobreposições legítimas geram aviso.
- Coincidência com DS/DC é calculada por consulta ao `CycleCalculator`, sem alterar o ciclo.
- Compensação é apenas registada; não cria FF nem FC.

### Migração
- Criada e aplicada a migração `b67e7ed6d0f7_create_unavailabilities.py`.
- Criadas apenas as tabelas `unavailabilities` e `unavailability_events`.
- Não foram alteradas migrações anteriores.
- Não foram criados militares, indisponibilidades, eventos fictícios, escalas, FF ou FC.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260728_0907_v06_pre_migration.db`.

### Testes
- Adicionados testes de modelo, validação, estados, sobreposições, intervalos, deslocações, integração com restrições, integração com ciclo, compensação, caso real prioritário, rotas e isolamento.
- Suite completa validada com `149 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` pertenças.
- A base real ficou com `0` referências do ciclo.
- A base real ficou com `0` restrições individuais.
- A base real ficou com `0` indisponibilidades.
- A base real ficou com `0` eventos de indisponibilidade.
- Revisão Alembic atual: `b67e7ed6d0f7`.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem grelha mensal, geração de escala, atribuições AT/PO/PT, descanso entre serviços, diagnósticos globais, FF, FC, Ronda, CR, remunerados, exportações, autenticação completa e auditoria funcional genérica.

## v0.5 - 2026-07-27

### Adicionado
- Criada gestão de restrições individuais dos militares.
- Adicionado modelo `MilitaryRestriction`.
- Adicionado serviço central `app/services/restriction_evaluator.py` para avaliar compatibilidade de um militar com uma data e janela horária.
- Adicionados tipos `UNAVAILABLE`, `AVAILABLE_ONLY` e `SPECIAL_AVAILABILITY`.
- Criadas páginas para listagem global, listagem por militar, criação, detalhe, edição, ativação, desativação e teste de compatibilidade.
- Integrado resumo de restrições ativas na ficha do militar.

### Regras
- `UNAVAILABLE` é restrição absoluta e bloqueia sempre quando aplicável.
- `SPECIAL_AVAILABILITY` só permite exatamente o período registado e não remove restrições absolutas.
- `AVAILABLE_ONLY` limita a disponibilidade aos períodos registados.
- Quando há conflito, prevalece a regra mais restritiva.
- Sem dias da semana selecionados significa todos os dias dentro do período de validade.
- Janelas de dia inteiro, janelas normais e janelas que atravessam a meia-noite são suportadas.
- Registos são preservados por histórico; ativar/desativar não elimina dados.

### Migração
- Criada e aplicada a migração `671d9ca0bf61_create_military_restrictions.py`.
- Criada apenas a tabela `military_restrictions`.
- Não foram alteradas migrações anteriores.
- Não foram criados dados iniciais, fictícios ou demonstrativos.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260727_170839.db`.

### Testes
- Adicionados testes de modelo, validação, dias da semana, dia inteiro, janelas horárias, períodos noturnos, prioridade, disponibilidade especial, rotas e isolamento.
- Suite completa validada com `120 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` pertenças.
- A base real ficou com `0` referências do ciclo.
- A base real ficou com `0` restrições individuais.
- Revisão Alembic atual: `671d9ca0bf61`.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem indisponibilidades LF, BM, DIL, tribunal, inquérito ou equivalentes.
- Sem geração de escala, grelha mensal, atribuições AT/PO/PT, diagnósticos, FF, FC, remunerados, exportações, autenticação completa e auditoria funcional genérica.

## v0.4 - 2026-07-27

### Adicionado
- Criada gestão de referências oficiais do ciclo de folgas por equipa.
- Adicionado modelo `TeamCycleReference`.
- Adicionado serviço central `app/services/cycle_calculator.py`.
- Criadas páginas para consulta geral do ciclo, configuração, histórico e pré-visualização.
- Integradas ligações do ciclo nas páginas de equipas e na ficha de militares com equipa.
- Adicionada explicação do cálculo com referência, semanas normalizadas, diferença de semanas, fase e código resultante.

### Regras
- Cada fase corresponde a uma semana operacional de segunda-feira a domingo.
- A data de referência é interpretada pela semana que a contém.
- O cálculo usa a segunda-feira da semana de referência e da semana consultada.
- A fase é calculada por diferença inteira de semanas e circulação entre `1` e `6`.
- `DS` e `DC` são calculados apenas pelo serviço central do ciclo.
- Não existe `DC` isolado nem inversão de `DS` e `DC`.
- Referências futuras preservam histórico e encerram a referência anterior no dia imediatamente anterior.
- Períodos sobrepostos por equipa são bloqueados.

### Migração
- Criada e aplicada a migração `6706124b423b_create_team_cycle_references.py`.
- Criada apenas a tabela `team_cycle_references`.
- Não foram inseridas referências de ciclo.
- Não foram alteradas migrações anteriores.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260727_163936.db`.

### Testes
- Adicionados testes de fases, continuidade mensal/anual, ano bissexto, normalização semanal, DS/DC, referências históricas, determinismo, rotas e caso real prioritário.
- Suite completa validada com `89 passed`.
- `compileall` executado com sucesso.

### Base de dados
- A base real ficou com `5` equipas oficiais.
- A base real ficou com `0` militares.
- A base real ficou com `0` pertenças.
- A base real ficou com `0` referências do ciclo.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem geração de escala, grelha mensal, AT, PO, PT, indisponibilidades, restrições, FF, FC, remunerados, exportações, autenticação completa e auditoria funcional genérica.

## v0.3 - 2026-07-27

### Adicionado
- Criada gestão de equipas oficiais e histórico de pertença.
- Adicionado modelo `Team` com códigos oficiais `A`, `B`, `C`, `D` e `E`.
- Adicionado modelo `MilitaryTeamHistory` para preservar períodos de pertença.
- Criadas rotas para listar e consultar equipas.
- Criadas rotas para associar equipa, mudar equipa e consultar/editar histórico por militar.
- Adicionados serviços e validadores dedicados para equipas e pertenças.
- Integrada indicação de equipa atual na lista e ficha de militares.

### Regras
- Apenas militares `PATRULHEIRO` podem pertencer a equipas.
- Militares `SEC`, `SI` e `CMD` ficam bloqueados para associação a equipa.
- Um militar só pode ter uma pertença atual.
- Períodos históricos não podem sobrepor-se.
- A semântica de datas é inclusiva: se a nova equipa começa num dia, a pertença anterior termina no dia imediatamente anterior.
- Alterações manuais ao histórico são preservadas por registos datados; não há eliminação automática de histórico.

### Migração
- Criada e aplicada a migração `6a09479ecf71_create_teams_and_memberships.py`.
- Criadas apenas as tabelas `teams` e `military_team_history`.
- Inseridas apenas as cinco equipas oficiais estruturais `A-E`.
- Adicionado índice único parcial para impedir mais do que uma pertença atual por militar.
- Criada cópia de segurança prévia da base real em `instance/backups/escala_20260727_155044.db`.

### Testes
- Adicionados testes para equipas oficiais, unicidade, código inválido, rotas, associação, mudança, histórico por data, bloqueio por tipo funcional e rollback.
- Suite completa validada com `45 passed`.

### Base de dados
- Não foram criados militares.
- Não foram criadas pertenças de equipa.
- Não foram criadas escalas.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem motor de ciclo, DS/DC, geração de escala, indisponibilidades, FF, FC, remunerados, exportações, autenticação completa e auditoria funcional genérica.

## v0.2 - 2026-07-27

### Adicionado
- Criada gestão de militares do efetivo.
- Adicionado modelo `Military` com `name`, `nim`, `functional_type`, `is_active`, `start_date`, `end_date`, `notes`, `created_at` e `updated_at`.
- Adicionado enum `FunctionalType` com `PATRULHEIRO`, `SEC`, `SI` e `CMD`.
- Criadas rotas para listar, criar, consultar, editar, ativar e desativar militares.
- Criados serviço e validador dedicados para regras de militares.
- Criados templates de listagem, criação, edição, detalhe e formulário parcial.

### Migração
- Criada e aplicada a migração `2ac4ce2a1e70_create_militaries_table.py`.
- Criada apenas a tabela `militaries`.
- Criada unicidade para `nim` e índices para filtros relevantes.

### Interface
- Aplicada fonte Segoe UI.
- Corrigidos textos principais com acentuação.
- Adicionadas mensagens de sucesso, erros junto aos campos e estado vazio profissional.

### Testes
- Adicionados testes de modelo, serviço, validações, rotas e isolamento da base de testes.
- Suite completa validada com `27 passed`.

### Base de dados
- Não foram criados militares na base real.
- Não foram criadas equipas.
- Não foram criadas escalas.
- Não foram criados dados fictícios ou demonstrativos.

### Limitações
- Sem equipas e sem histórico de pertença.
- Sem ciclo de folgas, escala mensal, indisponibilidades, FF, FC, remunerados, exportações, autenticação completa e auditoria funcional genérica.
- CSRF fica pendente para integração futura.

## Documentacao - 2026-07-27

### Adicionado
- Criado `docs/TEST_CASES.md` como documento normativo de testes.
- Definidos cenarios de validacao funcional, tecnica, regressao, seguranca, migracoes, exportacao e aceitacao manual.
- Incluida matriz de rastreabilidade entre regras operacionais e casos de teste.

### Sem alteracoes de codigo
- Nao foram alterados ficheiros de codigo.
- Nao foram implementadas funcionalidades.

### Base de dados
- Nao foram executadas migracoes.
- Nao foram alterados modelos.
- Nao foram criados dados reais, ficticios ou demonstrativos.

## v0.1 - 2026-07-27

### Adicionado
- Criada infraestrutura Flask com Application Factory.
- Adicionadas configuracoes separadas para desenvolvimento, testes e producao local.
- Configurados SQLAlchemy, Flask-Migrate e SQLite em `instance/escala.db`.
- Criado blueprint principal com pagina inicial e rota `/health`.
- Adicionado tratamento basico de erros 404 e 500.
- Adicionados logs tecnicos em `logs/`.
- Adicionados testes de arranque da aplicacao e isolamento da base de dados de testes.

### Base de dados
- Nao foram criados modelos funcionais.
- Nao foram criadas tabelas operacionais.
- Nao foram criados dados iniciais, reais, ficticios ou de demonstracao.

### Migracoes
- Flask-Migrate foi configurado para inicializacao das migracoes.
