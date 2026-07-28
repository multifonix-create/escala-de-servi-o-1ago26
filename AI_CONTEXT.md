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

Versão atual: `v0.6 - Indisponibilidades dos Militares`.

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

## Ainda Não Existe

Ainda não existem:

* geração da escala;
* grelha mensal;
* atribuição de AT;
* atribuição de PO;
* atribuição de PT;
* atribuição de DS/DC por militar;
* registos diários;
* motor de geração;
* autenticação completa;
* auditoria funcional genérica;
* diagnósticos completos;
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

* A base real contém as tabelas `militaries`, `teams`, `military_team_history`, `team_cycle_references`, `military_restrictions`, `unavailabilities` e `unavailability_events`.
* A base real contém apenas dados estruturais oficiais das equipas `A-E`.
* A base real não contém militares, pertenças de equipa, referências de ciclo, restrições individuais, indisponibilidades nem eventos de indisponibilidade após a v0.6.
* As referências do ciclo devem ser configuradas manualmente pelo utilizador.
* As equipas oficiais não têm rotas de criação, edição, desativação ou eliminação.
* Não foi implementada eliminação definitiva.
* Restrições individuais não são ainda usadas por um motor de geração de escala.
* Indisponibilidades já são registáveis, mas ainda não alimentam geração automática de escala.
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
149 passed
```

Os testes usam base SQLite em memória e não utilizam `instance/escala.db`.

## Próxima Etapa Recomendada

`v0.7 - Grelha Mensal da Escala`.
