# Changelog

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
