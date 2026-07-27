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

Versão atual: `v0.3 - Gestão de Equipas e Histórico de Pertença`.

Não existe repositório Git inicializado nesta pasta. Antes de migrações reais, deve ser criada cópia de segurança de `instance/escala.db`.

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
* inserção controlada das cinco equipas oficiais na migração;
* uma pertença atual por militar;
* histórico de pertença preservado por datas;
* semântica de datas inclusiva: se uma nova equipa começa em `2026-03-10`, a anterior termina em `2026-03-09`;
* associação e mudança permitidas apenas para militares `PATRULHEIRO`;
* bloqueio de alteração para `SEC`, `SI` ou `CMD` quando existir pertença atual;
* rotas e templates para listagem/detalhe de equipas, associação, mudança e histórico;
* testes automatizados de modelos, serviços, rotas, regras e rollback.

Rotas principais da v0.3:

* `GET /equipas`;
* `GET /equipas/<id>`;
* `GET /militares/<id>/equipa`;
* `POST /militares/<id>/equipa/associar`;
* `GET /militares/<id>/equipa/mudar`;
* `POST /militares/<id>/equipa/mudar`;
* `GET /militares/<id>/historico-equipas`;
* `GET /militares/<id>/historico-equipas/<membership_id>/editar`;
* `POST /militares/<id>/historico-equipas/<membership_id>/editar`.

## Ainda Não Existe

Ainda não existem:

* motor de ciclo;
* DS ou DC;
* geração da escala;
* escala mensal;
* indisponibilidades;
* restrições horárias;
* autenticação completa;
* auditoria funcional genérica;
* diagnósticos;
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
* criar escalas fictícias;
* criar dados demonstrativos na base real;
* apagar ou recriar a base de dados;
* usar `drop_all()` na base real;
* usar `db.create_all()` no arranque da aplicação;
* substituir a aplicação existente por uma nova;
* remover funcionalidades existentes;
* avançar para várias funcionalidades grandes simultaneamente.

## Decisões e Limitações Atuais

* A base real contém as tabelas `militaries`, `teams` e `military_team_history`.
* A base real contém apenas dados estruturais oficiais das equipas `A-E`.
* A base real não contém militares nem pertenças de equipa após a v0.3.
* As equipas oficiais não têm rotas de criação, edição, desativação ou eliminação.
* Não foi implementada eliminação definitiva.
* Não foi implementada autenticação completa.
* Não foi implementada CSRF; os formulários usam POST e estão preparados para integração futura.
* Auditoria funcional genérica fica para versão futura.
* Modelos futuros devem ser criados por fases e através de migrações.
* Não implementar todas as entidades do `DATA_MODEL.md` de uma vez.
* Rever a gestão da `SECRET_KEY` antes de uso real.

## Testes

Suite atual:

```text
45 passed
```

Os testes usam base SQLite em memória e não utilizam `instance/escala.db`.

## Próxima Etapa Recomendada

`v0.4 - Referências e Cálculo do Ciclo de Folgas`.
