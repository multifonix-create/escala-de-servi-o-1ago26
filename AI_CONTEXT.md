# Contexto do Projeto - Escala de Serviço

## Localização

O projeto está localizado em:

```text
C:\Users\35191\Desktop\projeto escala codex julho 26
```

A pasta raiz aberta deve ser `projeto escala codex julho 26`.

## Estado Real do Projeto

O projeto não está vazio.

A infraestrutura existente deve ser sempre reutilizada. É proibido recriar a aplicação ou substituir a estrutura atual por uma nova.

Versão atual: `v1.3 - Geração Automática de PT e Serviços Adicionais`.

Antes de migrações reais, deve ser criada cópia de segurança de `instance/escala.db`.

## Infraestrutura Existente

Existem atualmente:

* Application Factory com `create_app()`;
* configuração de desenvolvimento, testes e produção local;
* Flask-SQLAlchemy;
* Flask-Migrate;
* blueprint principal;
* página inicial;
* rota `/health`;
* tratamento de erros 404 e 500;
* logs básicos;
* pasta `migrations/` inicializada;
* base SQLite configurada para `instance/escala.db`;
* base de dados de testes em memória.

## v0.2 - Gestão de Militares

A v0.2 está concluída com:

* modelo `Military`;
* enum `FunctionalType` com `PATRULHEIRO`, `SEC`, `SI` e `CMD`;
* tabela `militaries`;
* migração `2ac4ce2a1e70_create_militaries_table.py`;
* blueprint, serviço, validador, templates e testes de militares;
* ativação e desativação sem eliminação definitiva.

## v0.3 - Equipas e Histórico de Pertença

A v0.3 está concluída com:

* modelo `Team`;
* modelo `MilitaryTeamHistory`;
* equipas oficiais estruturais `A`, `B`, `C`, `D` e `E`;
* migração `6a09479ecf71_create_teams_and_memberships.py`;
* uma pertença atual por militar;
* histórico de pertença preservado por datas;
* associação e mudança permitidas apenas para militares `PATRULHEIRO`;
* bloqueio de alteração para `SEC`, `SI` ou `CMD` quando existir pertença atual.

## v0.4 - Referências e Ciclo de Folgas

A v0.4 está concluída com:

* modelo `TeamCycleReference`;
* tabela `team_cycle_references`;
* migração `6706124b423b_create_team_cycle_references.py`;
* serviço central `app/services/cycle_calculator.py`;
* referências históricas por equipa;
* criação controlada de nova referência sem alterar retroativamente períodos anteriores;
* uma referência válida por equipa e data;
* bloqueio de períodos sobrepostos;
* fases permitidas apenas entre `1` e `6`;
* cálculo determinístico para datas futuras e anteriores;
* normalização semanal por segunda-feira;
* cálculo de `DS`, `DC` ou ausência de folga;
* explicação do cálculo com referência usada, semanas normalizadas, diferença de semanas e fase calculada;
* pré-visualização do ciclo sem gravação de escala.

Semântica semanal:

* cada fase corresponde a uma semana operacional civil, de segunda-feira a domingo;
* a data de referência é interpretada como pertencendo à semana que a contém;
* a segunda-feira dessa semana é usada como base de cálculo;
* a diferença inteira de semanas determina a fase;
* o ciclo circula sempre de `1` a `6`;
* se a nova referência começa numa data futura, a referência anterior é encerrada no dia imediatamente anterior.

Rotas principais da v0.4:

* `GET /ciclo`;
* `GET /ciclo/configurar`;
* `GET /ciclo/pre-visualizar`;
* `GET /equipas/<id>/ciclo`;
* `GET /equipas/<id>/ciclo/nova-referencia`;
* `POST /equipas/<id>/ciclo/nova-referencia`;
* `GET /equipas/<id>/ciclo/historico`.

Adaptação ao `DATA_MODEL.md`:

* o pedido v0.4 usa `notes`; o `DATA_MODEL.md` menciona `reason`;
* a v0.4 implementa `notes`, mantendo a intenção funcional de observações/motivo sem criar utilizadores ou `created_by` antes da fase de autenticação.

## v0.5 - Restrições Individuais dos Militares

A v0.5 está concluída com:

* modelo `MilitaryRestriction`;
* tabela `military_restrictions`;
* migração `671d9ca0bf61_create_military_restrictions.py`;
* tipos de restrição `UNAVAILABLE`, `AVAILABLE_ONLY` e `SPECIAL_AVAILABILITY`;
* períodos de validade com data inicial obrigatória e data final opcional;
* restrições por dias da semana, com ausência de seleção interpretada como todos os dias do período;
* restrições de dia inteiro;
* janelas horárias normais e janelas que atravessam a meia-noite;
* ativação e desativação sem eliminação definitiva;
* serviço central `app/services/restriction_evaluator.py` para avaliar compatibilidade;
* bloqueio por restrições absolutas `UNAVAILABLE`;
* disponibilidade especial sem remoção de restrições absolutas;
* prevalência da regra mais restritiva;
* tester de compatibilidade por militar, data e período horário;
* resumo de restrições na ficha do militar;
* histórico preservado por registos datados e estado ativo/inativo.

Rotas principais da v0.5:

* `GET /restricoes`;
* `GET /militares/<id>/restricoes`;
* `GET /militares/<id>/restricoes/nova`;
* `POST /militares/<id>/restricoes/nova`;
* `GET /militares/<id>/restricoes/<restriction_id>`;
* `GET /militares/<id>/restricoes/<restriction_id>/editar`;
* `POST /militares/<id>/restricoes/<restriction_id>/editar`;
* `POST /militares/<id>/restricoes/<restriction_id>/ativar`;
* `POST /militares/<id>/restricoes/<restriction_id>/desativar`;
* `GET /militares/<id>/restricoes/testar`;
* `POST /militares/<id>/restricoes/testar`.

## v0.6 - Indisponibilidades dos Militares

A v0.6 está concluída com:

* modelo `Unavailability`;
* modelo `UnavailabilityEvent`;
* tabelas `unavailabilities` e `unavailability_events`;
* migração `b67e7ed6d0f7_create_unavailabilities.py`;
* códigos `LF`, `LP`, `BM`, `LC`, `LN`, `DIL`, `TRIB`, `INQ`, `FORMACAO`, `TIRO` e `OUTRA`;
* estados `PLANNED`, `CONFIRMED` e `CANCELLED`;
* estados de compensação `NOT_APPLICABLE`, `PENDING_DECISION`, `GENERATES_CREDIT` e `DOES_NOT_GENERATE_CREDIT`;
* indisponibilidades de dia completo, intervalos parciais e intervalos contínuos multi-dia;
* deslocações antes e depois consideradas no intervalo efetivo;
* deteção de duplicados exatos e avisos de sobreposição;
* cancelamento sem eliminação física;
* eventos mínimos de histórico para criação, edição e transições;
* serviço central `app/services/unavailability_evaluator.py`;
* serviço combinado `app/services/availability_evaluator.py` para indisponibilidades e restrições;
* consulta ao ciclo via `CycleCalculator` para identificar coincidências com DS/DC;
* registo de compensação sem criação automática de FF ou FC;
* testador manual de compatibilidade.

Rotas principais da v0.6:

* `GET /indisponibilidades`;
* `GET /militares/<id>/indisponibilidades`;
* `GET /militares/<id>/indisponibilidades/nova`;
* `POST /militares/<id>/indisponibilidades/nova`;
* `GET /militares/<id>/indisponibilidades/<unavailability_id>`;
* `GET /militares/<id>/indisponibilidades/<unavailability_id>/editar`;
* `POST /militares/<id>/indisponibilidades/<unavailability_id>/editar`;
* `POST /militares/<id>/indisponibilidades/<unavailability_id>/confirmar`;
* `POST /militares/<id>/indisponibilidades/<unavailability_id>/cancelar`;
* `POST /militares/<id>/indisponibilidades/<unavailability_id>/reativar`;
* `GET /militares/<id>/indisponibilidades/testar`;
* `POST /militares/<id>/indisponibilidades/testar`.

## v0.7 - Grelha Mensal da Escala

A v0.7 está concluída com:

* modelo `ScheduleMonth`;
* modelo `ScheduleVersion`;
* tabelas `schedule_months` e `schedule_versions`;
* migração `91f6d17e963f_create_schedule_months_and_versions.py`;
* estados `NOT_GENERATED`, `DRAFT`, `VALIDATED`, `PUBLISHED` e `CLOSED`;
* origens de versão `INITIAL`, `MANUAL` e `SYSTEM`;
* criação controlada de mês em estado `DRAFT`;
* criação de versão inicial `1` com origem `INITIAL`;
* blueprint `schedules_bp`;
* seletor de mês e ano;
* consulta de mês vazio sem criação automática;
* grelha mensal com militares em linhas e dias em colunas;
* serviço central `app/services/monthly_grid_builder.py`;
* leitura dinâmica de DS/DC via `CycleCalculator`;
* leitura dinâmica de pertença por dia via histórico de equipa;
* apresentação visual de indisponibilidades planeadas e confirmadas;
* apresentação de indicadores de restrições, sem as tornar código principal;
* avisos para falta de militares, equipa ou referência de ciclo;
* consulta simples de histórico de versões.

Rotas principais da v0.7:

* `GET /escala`;
* `GET /escala/<year>/<month>`;
* `POST /escala/<year>/<month>/criar`;
* `GET /escala/<year>/<month>/versoes`;
* `GET /escala/<year>/<month>/versoes/<version_id>`.

Decisão de arquitetura da v0.7:

* não foi criada tabela de atribuições/células da escala;
* a grelha mensal é uma consulta calculada a partir das fontes de verdade existentes;
* não foram criados meses, versões ou células na base real para demonstração;
* feriados ainda não têm módulo próprio e são tratados como pendência.

## v0.8 - Edição Manual e Preservação de Alterações

A v0.8 está concluída com:

* modelo `Assignment`;
* modelo `AssignmentChange`;
* tabelas `assignments` e `assignment_changes`;
* migração `465d32473e31_create_assignments_and_assignment_.py`;
* catálogo central de códigos manuais em `app/services/assignment_codes.py`;
* serviço central `app/services/assignment_service.py`;
* edição manual célula a célula em versões `DRAFT`;
* atribuições manuais persistidas;
* bloqueio e desbloqueio de célula;
* limpeza lógica da célula através de `is_cleared`, preservando histórico;
* histórico com `CREATED`, `UPDATED`, `CLEARED`, `LOCKED`, `UNLOCKED`, `OVERRIDE_APPLIED` e `OVERRIDE_REMOVED`;
* validação contra estado da versão, período do militar, códigos permitidos, ciclo, equipa, referência de ciclo, indisponibilidades e restrições;
* override explícito com motivo obrigatório quando há avisos ultrapassáveis;
* BM confirmada bloqueada sem override normal;
* integração das atribuições manuais no `MonthlyGridBuilder`;
* indicadores visuais para manual, bloqueado e override.

Rotas principais da v0.8:

* `GET /escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>`;
* `POST /escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>`;
* `POST /escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>/limpar`;
* `POST /escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>/bloquear`;
* `POST /escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>/desbloquear`;
* `GET /escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>/historico`.

Decisões de arquitetura da v0.8:

* a edição manual não cria serviços automaticamente;
* a escrita manual de `DS` ou `DC` não altera o ciclo;
* a escrita manual de códigos de indisponibilidade não cria indisponibilidades;
* a escrita manual de `FF` ou `FC` não cria nem consome créditos;
* a grelha apresenta primeiro a atribuição manual persistida e mantém os dados subjacentes.

## v0.9 - Diagnóstico Inicial da Escala

A v0.9 está concluída com:

* modelo `DiagnosticRun`;
* modelo `DiagnosticIssue`;
* tabelas `diagnostic_runs` e `diagnostic_issues`;
* migração `1a69c7554b89_create_diagnostic_runs_and_issues.py`;
* serviço central `app/services/diagnostic_service.py`;
* catálogo de horários formalizados `app/services/service_code_catalog.py`;
* níveis `ERROR`, `WARNING` e `INFO`;
* categorias `CONFIGURATION`, `MILITARY`, `TEAM`, `CYCLE`, `UNAVAILABILITY`, `RESTRICTION`, `ASSIGNMENT`, `SCHEDULE_STATE`, `COVERAGE`, `REST`, `COMPENSATION` e `SYSTEM`;
* persistência de execuções e problemas de diagnóstico;
* reexecução preservando histórico;
* diagnóstico de configuração, militares, ciclo, indisponibilidades, restrições, atribuições, estados, cobertura parcial e descanso parcial;
* páginas de diagnóstico, filtros e detalhe de problema;
* indicador discreto `D` na grelha para células afetadas pelo último diagnóstico.

Rotas principais da v0.9:

* `GET /escala/<year>/<month>/versoes/<version_id>/diagnostico`;
* `POST /escala/<year>/<month>/versoes/<version_id>/diagnostico/executar`;
* `GET /escala/<year>/<month>/versoes/<version_id>/diagnostico/<run_id>`;
* `GET /escala/<year>/<month>/versoes/<version_id>/diagnostico/<run_id>/problemas/<issue_id>`.

Decisões de arquitetura da v0.9:

* o diagnóstico é independente da geração e não altera a escala;
* os resultados são persistidos para histórico e comparação futura;
* cobertura é apenas parcial e informativa sobre códigos manuais;
* descanso usa apenas horários formalizados de AT1-AT3 e PO1-PO3;
* códigos sem horário geram informação de diagnóstico não disponível.

## v1.0 - Geração Automática Inicial de AT e PO

A v1.0 está concluída com:

* modelo `GenerationRun`;
* modelo `AssignmentSelectionDetail`;
* tabelas `generation_runs` e `assignment_selection_details`;
* migração `a284728b2308_create_generation_runs_and_selection_.py`;
* serviço central `app/services/schedule_generator.py`;
* `ScheduleGenerator` para execução transacional da geração;
* `CandidateSelector` para elegibilidade, exclusões, ordenação e explicação;
* geração limitada a `AT1`, `AT2`, `AT3`, `PO1`, `PO2` e `PO3`;
* mínimos diários `AT=1` por turno e `PO=2` por turno;
* ordem fixa `AT1`, `PO1`, `AT2`, `PO2`, `AT3`, `PO3`;
* ordenação determinística sem `random`;
* período de equidade por defeito: mês atual mais três meses anteriores existentes;
* preservação de todas as atribuições manuais, bloqueadas ou não;
* criação de atribuições automáticas com `source=SYSTEM`, `is_manual=False`, `is_locked=False` e `has_override=False`;
* criação de `AssignmentChange` do tipo `CREATED` para atribuições automáticas;
* exclusão de `CMD` para AT/PO;
* uso de `SEC` e `SI` apenas quando não há patrulheiros elegíveis suficientes;
* respeito por DS/DC, indisponibilidades confirmadas e planeadas, restrições e descanso mínimo de oito horas;
* execução de diagnóstico final após a geração;
* diagnóstico de cobertura completo para versões com geração concluída;
* páginas de confirmação, lista e detalhe de gerações.

Rotas principais da v1.0:

* `POST /escala/<year>/<month>/versoes/<version_id>/gerar`;
* `GET /escala/<year>/<month>/versoes/<version_id>/geracoes`;
* `GET /escala/<year>/<month>/versoes/<version_id>/geracoes/<run_id>`.

Decisões de arquitetura da v1.0:

* a geração atua sobre uma versão `DRAFT` existente;
* não cria nova versão automaticamente;
* o modo implementado é apenas completar células vazias;
* automáticos anteriores não são removidos nesta versão;
* falta de cobertura não é falha técnica e fica explicada;
* não existe correção automática de diagnósticos.

## v1.1 - Regeneração Segura de Atribuições Automáticas AT/PO

A v1.1 está concluída com:

* campos opcionais `parent_version_id` e `generation_mode` em `ScheduleVersion`;
* campos opcionais `generation_mode`, `source_version_id` e `result_version_id` em `GenerationRun`;
* migração `a999dc4dceba_add_safe_regeneration_metadata.py`;
* `GenerationMode` com `FILL_EMPTY` e `REGENERATE_AUTOMATIC`;
* serviço central `app/services/schedule_regeneration.py`;
* `ScheduleRegenerationService` para criar nova versão e regenerar automáticos;
* comparação consultiva entre versões;
* página de confirmação explícita antes de regenerar;
* rota de comparação entre versão de origem e versão resultante;
* preservação integral da versão anterior;
* cópia apenas de atribuições manuais/importadas visíveis;
* não cópia de automáticos antigos;
* células limpas continuam sem código ativo;
* diagnóstico final associado à nova versão.

Rotas principais da v1.1:

* `GET /escala/<year>/<month>/versoes/<version_id>/regenerar`;
* `POST /escala/<year>/<month>/versoes/<version_id>/regenerar`;
* `GET /escala/<year>/<month>/versoes/<version_id>/comparar/<other_version_id>`.

Decisões de arquitetura da v1.1:

* regeneração nunca atua diretamente sobre a versão anterior;
* a versão resultante é sempre nova, `DRAFT`, `source=SYSTEM` e ligada à origem;
* `DRAFT` e `VALIDATED` podem originar nova versão;
* `PUBLISHED` e `CLOSED` ficam bloqueadas;
* rollback remove a nova versão se a regeneração falhar antes do commit;
* não há remoção destrutiva de automáticos na versão atual.

## v1.2 - Otimização e Desempenho do Motor AT/PO

A v1.2 está concluída com:

* `GenerationContext` reforçado com dados pré-carregados;
* caches locais por execução para equipa por militar/data e ciclo por equipa/data;
* pré-carregamento de pertenças, referências, restrições e indisponibilidades no gerador;
* seleção de candidatos sem queries por candidato/turno para ciclo, restrições e indisponibilidades;
* `MonthlyGridBuilder` otimizado com carregamento em lote por mês;
* `DiagnosticContext` otimizado com mapas em memória;
* testes de regressão de queries em `tests/test_performance.py`;
* nenhuma alteração de regras operacionais;
* nenhuma migração nova.

Medições principais v1.2:

```text
Geração 25: 28.581s / 51.232 queries -> 2.978s / 6.973 queries
Geração 50: 56.994s / 108.080 queries -> 5.359s / 12.134 queries
Regeneração 50: 58.627s / 108.071 queries -> 6.638s / 12.149 queries
Grelha 50: 3.991s / 8.132 queries -> 0.117s / 287 queries
Diagnóstico 50: 0.800s / 1.220 queries -> 0.082s / 384 queries
Geração 100: 102.909s / 182.353 queries -> 10.344s / 22.754 queries
Suite completa: 200 testes em 171.65s -> 203 testes em 53.24s
```

Decisões da v1.2:

* não foram criados índices novos;
* não foi criada migração;
* não foi criada cache global;
* os testes continuam a usar base SQLite em memória;
* a base real não foi usada para benchmarks.

## v1.3 - Geração Automática de PT e Serviços Adicionais

A v1.3 está concluída com:

* geração automática opcional de `PT`;
* `PT` desativado por defeito;
* parâmetros explícitos por execução em `GenerationRun.parameters_json`;
* duração permitida apenas de 6 ou 8 horas;
* hora inicial obrigatória quando PT é ativado;
* cálculo de hora final e `duration_minutes`;
* campos opcionais `start_time`, `end_time` e `duration_minutes` em `assignments`;
* migração `adaa03cbb54b_add_pt_assignment_timing_fields.py`;
* geração de PT apenas depois de AT/PO do dia estar completo;
* regra conservadora: sem PT num dia com cobertura AT/PO incompleta;
* PT apenas para militares sobrantes elegíveis;
* exclusão de `CMD`;
* `SEC` e `SI` excluídos por defeito do PT automático;
* respeito por DS/DC, indisponibilidades, restrições e descanso mínimo;
* preservação de PT manual;
* PT manual conta para limite diário;
* regeneração recalcula PT automático e preserva PT manual;
* detalhes de seleção `PT` em `assignment_selection_details`;
* diagnóstico específico para PT;
* grelha mensal com horário, duração e origem de PT quando existirem.

Decisões da v1.3:

* `PT` não conta para cobertura obrigatória;
* ausência de PT nunca é erro;
* PT automático usa `source=SYSTEM`, `is_manual=False`, `is_locked=False` e `has_override=False`;
* horários de PT não são globais nem inventados: dependem dos parâmetros da execução;
* `FF`, `FC`, Ronda, CR, remunerados e exportações continuam fora do âmbito.

## Ainda Não Existe

Ainda não existem:

* registos diários;
* autenticação completa;
* auditoria funcional genérica;
* FF;
* FC;
* remunerados;
* exportações operacionais.

## Documentos Existentes

Existem atualmente:

* `docs/ESCALA_RULES.md`;
* `docs/ARCHITECTURE.md`;
* `docs/CODING_STANDARDS.md`;
* `docs/DATA_MODEL.md`;
* `docs/TEST_CASES.md`;
* `docs/CHANGELOG.md`;
* `README.md`.

`docs/TEST_CASES.md` é documento obrigatório de leitura antes de alterações ao projeto.

## ESCALA_RULES.md

`docs/ESCALA_RULES.md`:

* existe;
* está completo;
* possui 218 secções numeradas;
* termina na secção `218. Estado do documento`;
* é o documento normativo principal do projeto;
* nunca deve ser considerado vazio.

Todo o comportamento operacional deve respeitar este documento. O código nunca deve criar, alterar ou reinterpretar regras operacionais sem instrução explícita do utilizador.

## Ordem de Autoridade

Todas as alterações futuras devem respeitar esta ordem:

1. instrução atual do utilizador;
2. `docs/ESCALA_RULES.md`;
3. `docs/ARCHITECTURE.md`;
4. `docs/CODING_STANDARDS.md`;
5. `docs/DATA_MODEL.md`;
6. `docs/TEST_CASES.md`;
7. `AI_CONTEXT.md`;
8. código existente.

## Proibições

É proibido:

* criar militares fictícios;
* criar equipas fictícias;
* criar referências fictícias do ciclo na base real;
* criar escalas fictícias;
* criar dados demonstrativos na base real;
* apagar ou recriar a base de dados;
* usar `drop_all()` na base real;
* usar `db.create_all()` no arranque da aplicação;
* substituir a aplicação existente por uma nova;
* remover funcionalidades existentes;
* avançar para várias funcionalidades grandes simultaneamente.

## Decisões e Limitações Atuais

* A base real contém as tabelas `militaries`, `teams`, `military_team_history`, `team_cycle_references`, `military_restrictions`, `unavailabilities`, `unavailability_events`, `schedule_months`, `schedule_versions`, `assignments`, `assignment_changes`, `diagnostic_runs`, `diagnostic_issues`, `generation_runs` e `assignment_selection_details`.
* A base real contém apenas dados estruturais oficiais das equipas `A-E`.
* A base real não contém militares, pertenças de equipa, referências de ciclo, restrições individuais, indisponibilidades, eventos de indisponibilidade, meses de escala, versões de escala, atribuições, alterações de atribuição, execuções de diagnóstico, problemas de diagnóstico, execuções de geração nem detalhes de seleção após a v1.3.
* As referências do ciclo devem ser configuradas manualmente pelo utilizador.
* As equipas oficiais não têm rotas de criação, edição, desativação ou eliminação.
* Não foi implementada eliminação definitiva.
* Restrições individuais já são usadas pela geração automática AT/PO.
* Indisponibilidades registadas alimentam a geração automática AT/PO.
* A grelha mensal consulta DS/DC, indisponibilidades e restrições dinamicamente e sobrepõe atribuições manuais persistidas quando existirem.
* A compensação por DS/DC é apenas registada; não cria FF nem FC.
* Não foi implementada autenticação completa.
* Não foi implementada CSRF; os formulários usam POST e estão preparados para integração futura.
* Auditoria funcional genérica fica para versão futura.
* Modelos futuros devem ser criados por fases e através de migrações.
* Não implementar todas as entidades do `DATA_MODEL.md` de uma vez.
* Rever a gestão da `SECRET_KEY` antes de uso real.

## Testes

Suite atual:

```text
215 passed
```

Os testes usam base SQLite em memória e não utilizam `instance/escala.db`.

## Próxima Etapa Recomendada

`v1.4 - Observabilidade Técnica e Métricas de Execução`.
