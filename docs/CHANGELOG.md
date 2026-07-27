# Changelog

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
