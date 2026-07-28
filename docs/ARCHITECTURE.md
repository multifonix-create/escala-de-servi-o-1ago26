# Arquitetura da Aplicação — Escala de Serviço

**Projeto:** Escala de Serviço
**Documento:** `ARCHITECTURE.md`
**Versão:** 1.0
**Estado:** Normativo
**Tecnologia principal:** Python, Flask e SQLite
**Responsável funcional:** Comandante do Posto Territorial

---

## 1. Finalidade

Este documento define a arquitetura técnica da aplicação de gestão da Escala de Serviço.

O objetivo é garantir que o projeto:

* permaneça organizado durante a sua evolução;
* possa ser desenvolvido por etapas;
* preserve as funcionalidades existentes;
* implemente corretamente as regras operacionais;
* seja fácil de testar;
* permita corrigir erros sem afetar módulos não relacionados;
* mantenha todos os dados históricos;
* seja preparado para futuras expansões.

As regras operacionais encontram-se definidas no ficheiro:

```text
docs/ESCALA_RULES.md
```

Este documento não pode alterar ou reinterpretar essas regras.

Quando existir contradição entre a arquitetura técnica e o `ESCALA_RULES.md`, prevalece o `ESCALA_RULES.md`.

---

## 2. Princípios arquiteturais

A aplicação deve seguir os seguintes princípios:

1. Separar interface, lógica operacional e acesso à base de dados.
2. Não colocar regras da escala diretamente nas páginas HTML ou nas rotas Flask.
3. Centralizar o cálculo das folgas num único módulo.
4. Centralizar a geração automática da escala num único motor.
5. Centralizar as validações num sistema próprio de diagnóstico.
6. Preservar sempre as alterações manuais.
7. Registar em auditoria todas as decisões relevantes.
8. Não criar militares fictícios ou dados de demonstração.
9. Não apagar dados históricos durante regenerações.
10. Não utilizar escolhas aleatórias não registadas.
11. Garantir que a geração produz sempre o mesmo resultado quando os dados de entrada forem iguais.
12. Fazer alterações pequenas, testáveis e reversíveis.
13. Utilizar migrações para qualquer alteração da estrutura da base de dados.
14. Criar testes para todas as regras operacionais críticas.
15. Fazer cópia de segurança antes de operações potencialmente destrutivas.

---

## 3. Tecnologias

### 3.1. Backend

A aplicação será desenvolvida com:

* Python;
* Flask;
* Flask-SQLAlchemy;
* SQLAlchemy;
* Flask-Migrate;
* Alembic;
* SQLite.

### 3.2. Interface

A interface utilizará:

* HTML;
* CSS;
* JavaScript;
* templates Jinja2;
* pedidos assíncronos apenas quando necessários.

A aplicação deve privilegiar páginas renderizadas pelo servidor, evitando complexidade desnecessária.

A edição da escala pode utilizar JavaScript para proporcionar um comportamento semelhante a uma folha de cálculo.

### 3.3. Exportações

As exportações poderão utilizar:

* `openpyxl` para Excel;
* uma biblioteca de criação de PDF compatível com A3;
* biblioteca padrão `csv` para CSV.

A biblioteca definitiva de PDF deve ser escolhida apenas após testes de impressão e fidelidade visual.

### 3.4. Testes

Os testes devem utilizar:

* `pytest`;
* base de dados SQLite temporária;
* fixtures controladas;
* testes unitários;
* testes de integração;
* testes de regressão.

Os dados utilizados nos testes nunca devem ser introduzidos na base de dados real.

---

## 4. Estrutura geral do projeto

```text
escala-servico/
│
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── config.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── military.py
│   │   ├── team.py
│   │   ├── restriction.py
│   │   ├── unavailability.py
│   │   ├── service.py
│   │   ├── schedule.py
│   │   ├── holiday_credit.py
│   │   ├── remunerated_service.py
│   │   ├── history.py
│   │   ├── audit.py
│   │   └── user.py
│   │
│   ├── repositories/
│   │   ├── military_repository.py
│   │   ├── team_repository.py
│   │   ├── schedule_repository.py
│   │   ├── history_repository.py
│   │   └── audit_repository.py
│   │
│   ├── services/
│   │   ├── cycle_calculator.py
│   │   ├── schedule_generator.py
│   │   ├── candidate_selector.py
│   │   ├── balance_service.py
│   │   ├── restriction_service.py
│   │   ├── rest_calculator.py
│   │   ├── holiday_credit_service.py
│   │   ├── remunerated_service.py
│   │   ├── manual_edit_service.py
│   │   ├── schedule_state_service.py
│   │   ├── backup_service.py
│   │   └── export_service.py
│   │
│   ├── validators/
│   │   ├── base.py
│   │   ├── coverage_validator.py
│   │   ├── cycle_validator.py
│   │   ├── rest_validator.py
│   │   ├── restriction_validator.py
│   │   ├── availability_validator.py
│   │   ├── compatibility_validator.py
│   │   └── diagnostic_service.py
│   │
│   ├── routes/
│   │   ├── dashboard.py
│   │   ├── military.py
│   │   ├── teams.py
│   │   ├── restrictions.py
│   │   ├── unavailability.py
│   │   ├── schedules.py
│   │   ├── holiday_credits.py
│   │   ├── remunerated.py
│   │   ├── diagnostics.py
│   │   ├── audit.py
│   │   ├── exports.py
│   │   └── settings.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard/
│   │   ├── military/
│   │   ├── teams/
│   │   ├── schedules/
│   │   ├── diagnostics/
│   │   ├── audit/
│   │   └── settings/
│   │
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   │
│   ├── commands/
│   │   ├── init_database.py
│   │   ├── create_backup.py
│   │   └── verify_database.py
│   │
│   └── utils/
│       ├── dates.py
│       ├── enums.py
│       ├── exceptions.py
│       └── logging.py
│
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── fixtures/
│
├── docs/
│   ├── ESCALA_RULES.md
│   ├── ARCHITECTURE.md
│   ├── CODING_STANDARDS.md
│   ├── DATA_MODEL.md
│   ├── TEST_CASES.md
│   └── CHANGELOG.md
│
├── instance/
│   ├── escala.db
│   └── backups/
│
├── exports/
├── logs/
├── requirements.txt
├── run.py
├── README.md
├── AI_CONTEXT.md
└── .gitignore
```

---

## 5. Organização por camadas

### 5.1. Camada de apresentação

Inclui:

* rotas Flask;
* templates;
* formulários;
* componentes visuais;
* JavaScript da grelha da escala.

Esta camada deve:

* receber os pedidos do utilizador;
* apresentar dados;
* enviar comandos para a camada de serviços;
* mostrar avisos e diagnósticos.

Não deve calcular:

* ciclos de folga;
* prioridades;
* descanso;
* equilíbrio;
* disponibilidade;
* seleção de militares.

### 5.2. Camada de serviços

Contém a lógica da aplicação.

Exemplos:

* cálculo do ciclo;
* geração da escala;
* seleção de candidatos;
* validação;
* alterações manuais;
* criação de FF;
* serviços remunerados;
* exportações;
* backups.

Esta camada não deve depender diretamente de elementos HTML.

### 5.3. Camada de repositórios

Os repositórios centralizam as consultas e alterações da base de dados.

Exemplos:

* obter militares ativos numa data;
* obter indisponibilidades de um período;
* obter escala de determinado mês;
* obter histórico de serviços;
* guardar nomeações;
* guardar auditoria.

As consultas complexas não devem ficar espalhadas pelas rotas.

### 5.4. Camada de modelos

Os modelos representam as tabelas e relações da base de dados.

Os modelos devem conter apenas:

* campos;
* relações;
* validações estruturais simples;
* propriedades diretamente relacionadas com a entidade.

As regras complexas devem permanecer nos serviços.

### 5.5. Camada de validação

Cada regra deve possuir um validador independente sempre que possível.

O serviço de diagnóstico reúne os resultados dos vários validadores e apresenta-os de forma uniforme.

---

## 6. Criação da aplicação

A aplicação deve utilizar o padrão Application Factory.

Exemplo conceptual:

```python
def create_app(config_name=None):
    app = Flask(__name__)
    load_configuration(app, config_name)
    initialize_extensions(app)
    register_blueprints(app)
    register_commands(app)
    return app
```

Este padrão permite:

* executar testes com configurações próprias;
* trocar a base de dados;
* evitar importações circulares;
* organizar os módulos;
* criar futuras versões da aplicação sem reestruturar todo o projeto.

---

## 7. Base de dados

### 7.1. Regras gerais

A base de dados principal será SQLite.

O ficheiro deve ficar em:

```text
instance/escala.db
```

A base de dados não deve ficar dentro de uma pasta pública.

Todas as alterações de estrutura devem utilizar migrações.

É proibido apagar e recriar a base de dados como forma normal de atualizar a aplicação.

### 7.2. Identificadores

Todas as entidades principais devem possuir um identificador interno único.

Os números profissionais dos militares não devem ser utilizados como chave primária.

### 7.3. Datas e horas

As datas devem ser guardadas em formato próprio de data.

As horas devem ser guardadas em formato próprio de hora ou data e hora.

Não devem ser guardadas apenas como texto quando forem necessárias para cálculos.

### 7.4. Eliminação de dados

Sempre que possível, deve ser utilizada desativação lógica.

Exemplo:

```text
ativo = false
```

Em vez de eliminar definitivamente:

* militares;
* equipas;
* restrições históricas;
* códigos;
* utilizadores;
* serviços já utilizados.

A eliminação definitiva deve ser reservada para dados criados por erro e exigir confirmação.

---

## 8. Entidades principais

## 8.1. Militar

A entidade `Military` representa cada militar.

Campos principais:

* `id`;
* `professional_number`;
* `full_name`;
* `functional_group`;
* `team_id`;
* `start_date`;
* `end_date`;
* `active`;
* `can_drive`;
* `notes`;
* `created_at`;
* `updated_at`.

O grupo funcional deve utilizar valores controlados:

* `PATRULHEIRO`;
* `SEC`;
* `SI`;
* `CMD`.

Um patrulheiro ativo deve estar associado a uma equipa operacional ativa.

---

## 8.2. Equipa

A entidade `Team` representa uma equipa operacional.

Campos principais:

* `id`;
* `name`;
* `active`;
* `notes`;
* `created_at`;
* `updated_at`.

A referência do ciclo não deve ser guardada apenas diretamente na equipa, porque pode ser alterada ao longo do tempo.

Deve existir uma entidade própria de histórico de referências.

---

## 8.3. Referência do ciclo da equipa

A entidade `TeamCycleReference` deve possuir:

* `id`;
* `team_id`;
* `reference_date`;
* `reference_phase`;
* `valid_from`;
* `valid_until`;
* `created_by`;
* `created_at`;
* `reason`.

Esta estrutura permite alterar a referência no futuro sem destruir o histórico anterior.

Em cada data apenas pode existir uma referência válida para a equipa.

---

## 8.4. Restrição individual

A entidade `MilitaryRestriction` deve possuir:

* `id`;
* `military_id`;
* `restriction_type`;
* `description`;
* `start_date`;
* `end_date`;
* `start_time`;
* `end_time`;
* `active`;
* `forceable`;
* `notes`;
* `created_by`;
* `created_at`.

Tipos iniciais possíveis:

* apenas AT;
* não faz PT;
* não faz noites;
* não faz remunerados;
* não faz ronda;
* não conduz;
* limitação médica;
* limitação horária;
* limitação por dia da semana;
* outra.

---

## 8.5. Indisponibilidade

A entidade `Unavailability` deve possuir:

* `id`;
* `military_id`;
* `unavailability_type`;
* `start_datetime`;
* `end_datetime`;
* `display_code`;
* `with_compensation`;
* `notes`;
* `created_by`;
* `created_at`;
* `updated_at`.

Tipos iniciais:

* férias;
* baixa médica;
* licença;
* formação;
* curso;
* tribunal;
* diligência;
* dispensa;
* outra.

---

## 8.6. Código de serviço

A entidade `ServiceCode` representa um código utilizável na escala.

Campos principais:

* `id`;
* `code`;
* `name`;
* `category`;
* `start_time`;
* `end_time`;
* `crosses_midnight`;
* `required_staff`;
* `priority`;
* `active`;
* `allow_manual_override`;
* `counts_for_balance`;
* `notes`.

Categorias possíveis:

* operacional;
* descanso;
* indisponibilidade;
* comando;
* remunerado;
* administrativo;
* compensação;
* outro.

Os códigos oficiais podem ser criados na instalação inicial.

Isto não constitui criação de dados fictícios, porque são configurações estruturais do sistema.

A instalação nunca deve criar militares, equipas ou escalas fictícias.

---

## 8.7. Mês da escala

A entidade `ScheduleMonth` representa uma escala mensal.

Campos principais:

* `id`;
* `year`;
* `month`;
* `status`;
* `current_version_id`;
* `created_by`;
* `created_at`;
* `updated_at`;
* `validated_at`;
* `published_at`;
* `closed_at`.

Deve existir apenas uma escala mensal principal para cada combinação de ano e mês.

Os estados admitidos são:

* `NOT_GENERATED`;
* `DRAFT`;
* `VALIDATED`;
* `PUBLISHED`;
* `CLOSED`.

---

## 8.8. Versão da escala

A entidade `ScheduleVersion` preserva as diferentes versões do mês.

Campos principais:

* `id`;
* `schedule_month_id`;
* `version_number`;
* `origin`;
* `created_by`;
* `created_at`;
* `notes`;
* `is_current`.

Origens possíveis:

* geração inicial;
* regeneração;
* edição manual;
* validação;
* publicação;
* reabertura.

Uma versão publicada ou fechada não deve ser destruída quando existirem alterações posteriores.

---

## 8.9. Nomeação diária

A entidade `Assignment` representa a atribuição principal de um código a um militar numa data.

Campos principais:

* `id`;
* `schedule_version_id`;
* `military_id`;
* `assignment_date`;
* `service_code_id`;
* `start_datetime`;
* `end_datetime`;
* `origin`;
* `locked`;
* `manual_override`;
* `override_reason`;
* `execution_status`;
* `created_by`;
* `created_at`;
* `updated_at`.

Origens possíveis:

* ciclo;
* indisponibilidade;
* geração automática;
* alteração manual;
* importação;
* sistema.

Estados de execução possíveis:

* planeado;
* executado;
* não executado;
* substituído;
* cancelado.

Por regra, deve existir apenas uma nomeação principal por militar e por dia.

Serviços adicionais que possam coexistir devem utilizar uma entidade separada.

---

## 8.10. Serviço adicional

A entidade `AdditionalAssignment` permite registar atividades que não substituem o código principal.

Campos principais:

* `id`;
* `assignment_id`;
* `service_code_id`;
* `start_datetime`;
* `end_datetime`;
* `notes`;
* `created_by`;
* `created_at`.

Esta entidade não deve ser utilizada para contornar conflitos entre códigos principais incompatíveis.

---

## 8.11. Histórico de serviços

A entidade `ServiceHistory` deve permitir registar:

* histórico anterior à aplicação;
* histórico gerado;
* histórico executado;
* ajustes autorizados.

Campos principais:

* `id`;
* `military_id`;
* `service_code_id`;
* `quantity`;
* `history_type`;
* `reference_date`;
* `source_assignment_id`;
* `notes`;
* `created_at`.

Tipos:

* inicial;
* automático;
* executado;
* ajuste manual;
* importado.

---

## 8.12. Direito a FF

A entidade `HolidayLeaveCredit` representa uma FF adquirida por trabalho em feriado.

Campos principais:

* `id`;
* `military_id`;
* `holiday_date`;
* `source_assignment_id`;
* `service_performed`;
* `acquired_at`;
* `status`;
* `scheduled_date`;
* `used_date`;
* `cancelled_at`;
* `notes`;
* `created_by`;
* `scheduled_by`;
* `created_at`;
* `updated_at`.

Estados:

* `PENDING`;
* `SCHEDULED`;
* `USED`;
* `RESCHEDULED`;
* `CANCELLED`.

A combinação do militar, feriado e serviço de origem deve impedir a criação duplicada da mesma FF.

A FF só ocupa uma célula da escala quando estiver agendada.

---

## 8.13. Preferências de serviços remunerados

A entidade `RemuneratedPreference` deve possuir:

* `id`;
* `military_id`;
* `volunteer`;
* `volunteer_on_days_off`;
* `waives_eight_hour_rest`;
* `active_from`;
* `active_until`;
* `notes`.

A decisão de abdicar do descanso mínimo deve ser tratada como autorização específica e auditável.

---

## 8.14. Serviço remunerado

A entidade `RemuneratedAssignment` deve possuir:

* `id`;
* `military_id`;
* `table_type`;
* `service_date`;
* `start_datetime`;
* `end_datetime`;
* `status`;
* `selection_reason`;
* `non_volunteer_override`;
* `first_confirmation_by`;
* `second_confirmation_by`;
* `created_at`.

Tipos:

* Tabela A;
* Tabela B.

---

## 8.15. Diagnóstico

A entidade `DiagnosticIssue` guarda os resultados das verificações.

Campos principais:

* `id`;
* `schedule_version_id`;
* `military_id`;
* `assignment_date`;
* `validator_code`;
* `severity`;
* `message`;
* `details`;
* `authorized`;
* `authorized_by`;
* `authorized_at`;
* `resolution_status`;
* `created_at`.

Níveis:

* erro;
* aviso;
* informação;
* violação autorizada.

Os diagnósticos devem poder ser recalculados.

---

## 8.16. Auditoria

A entidade `AuditLog` deve registar:

* `id`;
* `user_id`;
* `action`;
* `entity_type`;
* `entity_id`;
* `schedule_month_id`;
* `previous_value`;
* `new_value`;
* `reason`;
* `warnings`;
* `confirmation_level`;
* `created_at`.

Os registos de auditoria não devem ser editáveis através da interface normal.

---

## 9. Motor do ciclo de folgas

O cálculo das folgas deve estar isolado em:

```text
app/services/cycle_calculator.py
```

A classe principal poderá chamar-se:

```text
CycleCalculator
```

Responsabilidades:

* carregar a referência válida da equipa;
* calcular os blocos de folga;
* avançar de fase para fase;
* gerar DS e DC;
* calcular períodos anteriores e posteriores;
* explicar a origem de cada folga;
* validar a continuidade do ciclo.

O motor não pode calcular a fase através de uma simples diferença de semanas.

Deve trabalhar com a sequência dos blocos:

```text
Fase 1 → sábado e domingo
Fase 2 → sexta-feira
Fase 3 → quinta-feira e sexta-feira
Fase 4 → quarta-feira e quinta-feira
Fase 5 → terça-feira e quarta-feira
Fase 6 → segunda-feira
Fase 1 → sábado e domingo
```

Depois de terminar um bloco, deve localizar o próximo bloco correspondente à fase seguinte.

Cada resultado deve indicar:

* equipa;
* fase;
* data do bloco;
* primeiro dia;
* segundo dia, quando exista;
* código DS;
* código DC, quando exista;
* referência utilizada.

O cálculo deve ser determinístico.

---

## 10. Motor de geração da escala

O motor principal deve estar em:

```text
app/services/schedule_generator.py
```

A classe principal poderá chamar-se:

```text
ScheduleGenerator
```

A geração deve ser executada por fases independentes.

### Fase 1 — Preparação

* criar ou carregar o mês;
* obter militares ativos;
* obter equipas ativas;
* verificar referências do ciclo;
* carregar códigos de serviço;
* carregar horários;
* carregar histórico;
* carregar restrições;
* carregar indisponibilidades;
* carregar alterações manuais preservadas.

### Fase 2 — Códigos prioritários

Aplicar:

1. alterações manuais bloqueadas;
2. indisponibilidades;
3. FF agendadas;
4. FC agendadas;
5. Ronda e CR previamente definidos;
6. DS e DC.

### Fase 3 — Cobertura operacional

Para cada dia:

1. preencher AT1;
2. preencher AT2;
3. preencher AT3;
4. preencher PO1 com dois militares;
5. preencher PO2 com dois militares;
6. preencher PO3 com dois militares.

A ordem concreta dentro de AT e PO pode ser configurada, mas nunca pode deixar de cumprir os mínimos.

### Fase 4 — PT

Depois de preenchidos todos os AT e PO:

* identificar militares operacionais disponíveis;
* excluir militares de folga;
* excluir militares indisponíveis;
* excluir militares com serviço;
* excluir militares impedidos de fazer PT;
* atribuir PT aos restantes, quando aplicável.

### Fase 5 — Equilíbrio

Aplicar critérios de equidade sem violar regras obrigatórias.

### Fase 6 — Diagnóstico

Executar todos os validadores.

### Fase 7 — Gravação

* criar nova versão;
* guardar nomeações;
* guardar diagnósticos;
* registar a operação em auditoria;
* definir o mês como rascunho.

---

## 11. Preservação de alterações manuais

As alterações manuais devem possuir o campo:

```text
locked = true
```

Por defeito, a regeneração deve preservar todas as células bloqueadas.

Antes de regenerar, o utilizador deve poder escolher:

* preservar todas as alterações manuais;
* preservar apenas alterações selecionadas;
* regenerar apenas células automáticas;
* remover alterações manuais após confirmação;
* cancelar.

A remoção de alterações manuais deve ficar registada em auditoria.

---

## 12. Seleção de candidatos

A seleção de militares deve estar isolada em:

```text
app/services/candidate_selector.py
```

O processo deve possuir duas etapas.

### 12.1. Exclusão obrigatória

Excluir candidatos que:

* não estejam ativos;
* não pertençam ao grupo funcional adequado;
* estejam indisponíveis;
* estejam de DS, DC, FF ou FC;
* já possuam serviço incompatível;
* não cumpram o descanso mínimo;
* tenham restrição incompatível;
* estejam fora do período de integração no efetivo;
* tenham alteração manual incompatível.

### 12.2. Ordenação

Os candidatos válidos devem ser ordenados com base em:

* menor número do serviço em causa;
* menor número no respetivo turno;
* menor número de noites;
* menor número de fins de semana;
* maior tempo desde o último serviço semelhante;
* distribuição por equipas;
* critérios adicionais aprovados.

O resultado deve ser determinístico.

Em caso de empate total, deve ser utilizado um critério estável, como:

* número profissional;
* identificador interno;
* ordem alfabética.

Nunca deve ser utilizada seleção aleatória sem registo.

### 12.3. Explicação da escolha

Cada nomeação automática deve poder apresentar:

* candidatos analisados;
* candidatos excluídos;
* razão da exclusão;
* critérios de ordenação;
* razão da escolha final.

---

## 13. Cálculo do descanso

O cálculo deve estar em:

```text
app/services/rest_calculator.py
```

O sistema deve comparar:

```text
fim do serviço anterior
início do serviço seguinte
```

Deve considerar:

* serviços que atravessam a meia-noite;
* serviços adicionais;
* serviços remunerados;
* Ronda;
* CR;
* alterações manuais;
* datas e horas reais.

O resultado deve indicar:

* horas disponíveis;
* mínimo obrigatório;
* serviços envolvidos;
* existência de autorização manual.

---

## 14. Sistema de diagnóstico

O serviço principal deve estar em:

```text
app/validators/diagnostic_service.py
```

Cada validador deve implementar uma interface comum.

Exemplo conceptual:

```python
class BaseValidator:
    code = ""
    description = ""

    def validate(self, context):
        raise NotImplementedError
```

Validadores iniciais:

* cobertura mínima;
* continuidade do ciclo;
* DS e DC;
* descanso;
* indisponibilidades;
* restrições;
* compatibilidade de códigos;
* duplicação de serviços;
* equipas;
* militares ativos;
* referências do ciclo;
* serviços fora do período de integração;
* categorias funcionais.

O diagnóstico deve poder ser executado:

* depois da geração;
* depois de uma alteração manual;
* antes da validação;
* antes da publicação;
* por pedido do utilizador.

---

## 15. Alteração manual de células

O serviço responsável deve estar em:

```text
app/services/manual_edit_service.py
```

Fluxo:

1. receber militar, data e novo código;
2. carregar o valor anterior;
3. simular a alteração;
4. executar os validadores relevantes;
5. apresentar avisos;
6. permitir cancelar;
7. permitir confirmar;
8. exigir justificação quando necessário;
9. guardar a alteração;
10. bloquear a célula;
11. criar nova versão ou atualizar o rascunho;
12. registar em auditoria;
13. recalcular o diagnóstico afetado.

A alteração manual nunca deve ser silenciosa quando viola uma regra.

---

## 16. Gestão de FF

O serviço deve estar em:

```text
app/services/holiday_credit_service.py
```

Responsabilidades:

* identificar serviço prestado em feriado;
* criar o direito a FF;
* impedir duplicações;
* apresentar FF pendentes;
* sugerir datas com disponibilidade;
* agendar a FF;
* reagendar;
* marcar como gozada;
* cancelar mediante justificação;
* manter histórico.

A criação definitiva do direito deve ocorrer quando o serviço prestado no feriado for confirmado.

Quando o mês for fechado, o sistema pode propor a criação das FF correspondentes aos serviços marcados como executados.

A FF não altera o ciclo da equipa.

---

## 17. Serviços remunerados

O módulo de remunerados deve ser independente do gerador principal, embora utilize:

* disponibilidade;
* descanso;
* restrições;
* histórico;
* preferências.

A ordenação deve seguir exatamente o `ESCALA_RULES.md`.

O sistema deve guardar os critérios utilizados em cada seleção.

A nomeação de não voluntários deve exigir dupla confirmação.

---

## 18. Estados e transições da escala

As transições permitidas devem ser controladas pelo:

```text
app/services/schedule_state_service.py
```

Transições principais:

```text
Não gerada → Rascunho
Rascunho → Validada
Validada → Publicada
Publicada → Fechada
```

Também devem ser possíveis, mediante confirmação:

```text
Validada → Rascunho
Publicada → Rascunho
Fechada → Rascunho
```

A reabertura deve:

* criar nova versão;
* preservar a versão publicada ou fechada;
* registar o motivo;
* identificar o utilizador;
* ficar em auditoria.

Uma escala com erros não autorizados não pode passar automaticamente para validada.

---

## 19. Páginas da aplicação

### 19.1. Painel inicial

Deve apresentar:

* mês atual;
* estado da escala;
* cobertura;
* erros;
* avisos;
* FF pendentes;
* indisponibilidades próximas;
* ações principais.

### 19.2. Militares

Deve permitir:

* listar;
* criar;
* editar;
* ativar;
* desativar;
* consultar histórico;
* gerir restrições;
* gerir remunerados;
* consultar FF.

### 19.3. Equipas

Deve permitir:

* criar equipas;
* editar nomes;
* ativar e desativar;
* definir referências;
* consultar o ciclo;
* pré-visualizar as folgas futuras.

### 19.4. Indisponibilidades

Deve permitir:

* criar;
* editar;
* eliminar mediante confirmação;
* filtrar;
* consultar por militar;
* consultar por período.

### 19.5. Escala mensal

Deve possuir:

* seletor de mês e ano;
* grelha semelhante a Excel;
* nomes nas linhas;
* dias nas colunas;
* códigos nas células;
* cores configuráveis;
* edição célula a célula;
* filtros;
* legenda;
* totais;
* avisos visuais.

### 19.6. Geração

Deve apresentar:

* período;
* militares incluídos;
* equipas;
* restrições;
* indisponibilidades;
* alterações preservadas;
* opções de geração;
* resultado;
* conflitos.

### 19.7. Diagnóstico

Deve permitir filtrar por:

* gravidade;
* data;
* militar;
* serviço;
* tipo de regra;
* estado de resolução.

### 19.8. FF

Deve apresentar:

* FF pendentes;
* FF agendadas;
* FF gozadas;
* origem;
* data do feriado;
* serviço executado;
* sugestões de datas;
* histórico.

### 19.9. Remunerados

Deve apresentar:

* voluntários;
* preferências;
* totais;
* última nomeação;
* Tabela A;
* Tabela B;
* ordem de seleção;
* histórico.

### 19.10. Auditoria

Deve permitir pesquisar por:

* utilizador;
* militar;
* data;
* mês;
* ação;
* entidade;
* alteração manual;
* confirmação.

### 19.11. Exportações

Deve permitir:

* PDF A3;
* Excel;
* CSV;
* seleção da versão;
* pré-visualização;
* identificação da data de exportação.

### 19.12. Definições

Deve incluir:

* códigos;
* horários;
* cores;
* cobertura mínima;
* feriados;
* cópias de segurança;
* utilizadores;
* parâmetros autorizados.

As regras estruturais não devem ser livremente alteráveis nesta página.

---

## 20. Rotas

As rotas devem ser organizadas através de Blueprints.

Exemplos:

```text
/dashboard
/militares
/militares/<id>
/equipas
/indisponibilidades
/escalas
/escalas/<ano>/<mes>
/escalas/<ano>/<mes>/gerar
/escalas/<ano>/<mes>/diagnostico
/ff
/remunerados
/auditoria
/exportacoes
/definicoes
```

Ações que alterem dados devem utilizar métodos HTTP adequados, como:

* POST;
* PUT;
* PATCH;
* DELETE.

Não devem ser efetuadas alterações de dados por simples abertura de uma rota GET.

---

## 21. Utilizadores e permissões

Mesmo sendo uma aplicação local, a arquitetura deve estar preparada para utilizadores.

Perfis iniciais:

### Comandante

Pode:

* gerir todos os dados;
* gerar escalas;
* editar manualmente;
* autorizar violações;
* validar;
* publicar;
* fechar;
* reabrir;
* consultar auditoria;
* fazer backups.

### Editor

Pode:

* gerir dados autorizados;
* editar rascunhos;
* registar indisponibilidades;
* não pode publicar ou fechar sem autorização.

### Consulta

Pode:

* consultar escalas;
* consultar relatórios;
* exportar quando autorizado;
* não pode alterar dados.

A instalação inicial pode possuir apenas um utilizador Comandante.

---

## 22. Auditoria técnica

Devem ser registadas, pelo menos:

* criação e edição de militares;
* ativação e desativação;
* mudanças de equipa;
* alterações das referências do ciclo;
* criação e alteração de restrições;
* indisponibilidades;
* geração;
* regeneração;
* alterações manuais;
* autorizações de violações;
* criação e uso de FF;
* nomeações remuneradas;
* mudança de estado;
* exportações;
* backups;
* restauros;
* migrações relevantes.

---

## 23. Exportações

O serviço deve estar em:

```text
app/services/export_service.py
```

Cada exportação deve utilizar uma estrutura de dados comum.

Não devem existir cálculos diferentes para:

* grelha apresentada;
* PDF;
* Excel;
* CSV.

Todos devem utilizar a mesma versão da escala e os mesmos dados.

Cada exportação deve indicar:

* mês;
* ano;
* versão;
* estado;
* data e hora;
* utilizador;
* identificação do ficheiro.

---

## 24. Cópias de segurança

O serviço deve estar em:

```text
app/services/backup_service.py
```

Os backups devem ser guardados em:

```text
instance/backups/
```

Deve ser criado backup antes de:

* migração da base de dados;
* restauro;
* eliminação em massa;
* regeneração destrutiva;
* alteração estrutural;
* importação de dados.

Nome recomendado:

```text
escala_YYYYMMDD_HHMMSS.db
```

A aplicação deve permitir:

* criar backup manual;
* listar backups;
* verificar integridade;
* restaurar mediante confirmação;
* preservar o ficheiro atual antes do restauro.

Os backups não devem ser incluídos no repositório Git.

---

## 25. Logs

Os logs técnicos devem ficar em:

```text
logs/
```

Devem existir níveis:

* DEBUG;
* INFO;
* WARNING;
* ERROR;
* CRITICAL.

Os logs não substituem a auditoria.

A auditoria regista ações funcionais.

Os logs registam o funcionamento técnico da aplicação.

---

## 26. Tratamento de erros

A aplicação deve possuir exceções próprias.

Exemplos:

* `CycleCalculationError`;
* `MissingTeamReferenceError`;
* `ScheduleGenerationError`;
* `InvalidAssignmentError`;
* `RestViolationError`;
* `ManualOverrideRequiredError`;
* `DuplicateHolidayCreditError`;
* `ScheduleStateError`.

Os erros apresentados ao utilizador devem ser claros.

Detalhes técnicos devem ficar nos logs e não ser apresentados integralmente na interface.

---

## 27. Testes

### 27.1. Testes unitários

Devem testar módulos isolados:

* cálculo do ciclo;
* DS e DC;
* descanso;
* prioridades;
* filtros de candidatos;
* equilíbrio;
* FF;
* remunerados;
* estados.

### 27.2. Testes de integração

Devem testar:

* geração completa;
* gravação na base de dados;
* alterações manuais;
* regeneração;
* validação;
* publicação;
* exportação.

### 27.3. Testes de regressão

Cada erro corrigido deve originar um teste que impeça o seu reaparecimento.

Exemplo obrigatório:

> Uma equipa que folga numa segunda-feira na Fase 6 deve passar para a Fase 1 e folgar no sábado e domingo seguintes previstos pelo ciclo, sem esperar por uma mudança semanal artificial.

### 27.4. Base de dados de testes

Os testes devem utilizar uma base de dados independente.

Nunca devem utilizar:

```text
instance/escala.db
```

---

## 28. Migrações

Qualquer alteração nos modelos deve incluir:

1. criação da migração;
2. revisão do ficheiro gerado;
3. backup da base de dados;
4. execução da migração;
5. teste de leitura dos dados existentes;
6. teste de reversão, quando possível;
7. atualização do `CHANGELOG.md`.

Não é permitido alterar manualmente tabelas da base de dados real sem migração, salvo recuperação de emergência documentada.

---

## 29. Configuração

Devem existir configurações separadas:

* desenvolvimento;
* testes;
* produção local.

Valores sensíveis não devem ser escritos diretamente no código.

Configurações possíveis:

* caminho da base de dados;
* chave secreta;
* pasta de backups;
* pasta de exportações;
* nível de logs;
* formato de data;
* idioma;
* endereço e porta.

Endereço local inicial:

```text
http://127.0.0.1:5000/
```

A porta deve poder ser alterada por configuração.

---

## 30. Segurança

Mesmo sendo local, a aplicação deve:

* utilizar autenticação;
* proteger formulários contra CSRF;
* validar todos os dados recebidos;
* impedir injeções;
* limitar tipos de ficheiro importados;
* proteger backups;
* não expor a base de dados;
* não guardar palavras-passe em texto simples;
* registar tentativas de acesso inválidas;
* terminar sessões inativas, quando configurado.

---

## 31. Inicialização da aplicação

Na primeira execução, a aplicação pode criar:

* tabelas;
* utilizador administrador;
* códigos oficiais;
* tipos de restrição;
* tipos de indisponibilidade;
* configurações básicas.

Não pode criar automaticamente:

* militares;
* equipas;
* escalas;
* indisponibilidades;
* restrições pessoais;
* serviços fictícios;
* histórico fictício.

---

## 32. Evolução da aplicação

As novas funcionalidades devem ser introduzidas por módulos.

Ordem recomendada:

1. estrutura base;
2. base de dados e migrações;
3. gestão de militares;
4. gestão de equipas;
5. referências e ciclo de folgas;
6. restrições;
7. indisponibilidades;
8. grelha mensal;
9. edição manual;
10. diagnóstico;
11. geração de AT e PO;
12. PT;
13. equidade;
14. FF;
15. remunerados;
16. estados;
17. auditoria;
18. exportações;
19. backups;
20. otimização da interface.

Nenhuma etapa deve remover ou reescrever desnecessariamente funcionalidades estáveis.

---

## 33-A. Estado implementado da grelha mensal na v0.7

A v0.7 introduz o módulo de consulta mensal em `/escala`.

Componentes implementados:

* modelo `ScheduleMonth`;
* modelo `ScheduleVersion`;
* blueprint `schedules_bp`;
* serviço `app/services/schedule_service.py`;
* builder `app/services/monthly_grid_builder.py`;
* templates em `app/templates/schedules/`.

Decisão técnica da v0.7:

* não existe tabela de células/atribuições da escala;
* a grelha é calculada em leitura a partir de militares, histórico de equipas, referências de ciclo, restrições e indisponibilidades;
* a criação de mês cria apenas estrutura em `DRAFT` e versão inicial;
* a geração operacional de serviços fica fora da v0.7;
* a edição manual e preservação de alterações ficam para a v0.8.

---

## 33-B. Estado implementado da edição manual na v0.8

A v0.8 introduz persistência de células manuais sobre a grelha mensal.

Componentes implementados:

* modelo `Assignment`;
* modelo `AssignmentChange`;
* serviço `app/services/assignment_service.py`;
* catálogo `app/services/assignment_codes.py`;
* templates de edição e histórico em `app/templates/schedules/`.

Decisão técnica da v0.8:

* uma célula limpa permanece como registo lógico com `is_cleared`, para preservar a ligação ao histórico;
* alterações manuais são apresentadas sobre a informação dinâmica calculada;
* versões fora de `DRAFT` bloqueiam edição normal;
* overrides exigem ação explícita e motivo;
* a edição manual não executa geração automática, não altera ciclo, não cria indisponibilidades e não cria FF/FC.

---

## 33-C. Estado implementado do diagnóstico na v0.9

A v0.9 introduz o diagnóstico inicial centralizado da escala.

Componentes implementados:

* modelo `DiagnosticRun`;
* modelo `DiagnosticIssue`;
* serviço `app/services/diagnostic_service.py`;
* catálogo `app/services/service_code_catalog.py`;
* páginas de diagnóstico em `app/templates/schedules/`.

Decisão técnica da v0.9:

* os diagnósticos são persistidos para preservar histórico;
* cada execução cria novo `DiagnosticRun`;
* problemas são preservados em `DiagnosticIssue`;
* o diagnóstico não altera células, estados, ciclo, indisponibilidades ou restrições;
* cobertura e descanso são parciais nesta fase;
* apenas AT1, AT2, AT3, PO1, PO2 e PO3 possuem horários usados pelo diagnóstico de descanso.

## 33-D. Estado implementado da geração na v1.0

A v1.0 introduz a geração automática inicial, limitada a AT e PO.

Componentes:

* `app/services/schedule_generator.py`;
* `ScheduleGenerator`;
* `CandidateSelector`;
* `GenerationRun`;
* `AssignmentSelectionDetail`.

Responsabilidades:

* validar versão `DRAFT`;
* contar cobertura já existente;
* preservar atribuições manuais;
* excluir candidatos inelegíveis;
* ordenar candidatos de forma determinística;
* criar apenas atribuições `SYSTEM`;
* guardar detalhes de seleção e exclusão;
* executar diagnóstico final.

Decisões:

* ordem fixa: `AT1`, `PO1`, `AT2`, `PO2`, `AT3`, `PO3`;
* modo único: completar células vazias;
* sem aleatoriedade;
* sem criação automática de nova versão;
* sem remoção de automáticos anteriores;
* sem PT, FF, FC, Ronda, CR ou remunerados;
* falta de cobertura é registada e explicada, não tratada como erro técnico.

## 33-E. Estado implementado da regeneração na v1.1

A v1.1 introduz a regeneração segura de automáticos AT/PO.

Componentes:

* `app/services/schedule_regeneration.py`;
* `ScheduleRegenerationService`;
* `compare_versions`;
* campos opcionais de ligação entre versões e execuções.

Fluxo:

1. validar versão de origem;
2. criar nova versão sequencial;
3. copiar apenas manuais/importados visíveis;
4. não copiar automáticos antigos;
5. gerar AT/PO sobre a nova versão;
6. executar diagnóstico final;
7. apresentar comparação consultiva.

Decisões:

* a versão anterior nunca é alterada;
* `DRAFT` e `VALIDATED` podem originar nova versão;
* `PUBLISHED` e `CLOSED` ficam bloqueadas;
* células limpas não reaparecem como código ativo;
* rollback remove a nova versão se houver falha antes da conclusão;
* não existe regeneração destrutiva na mesma versão.

## 33-F. Estado implementado da otimização na v1.2

A v1.2 otimiza desempenho sem alterar regras operacionais.

Áreas otimizadas:

* geração AT/PO;
* regeneração;
* construção da grelha mensal;
* diagnóstico;
* seleção de candidatos.

Decisões:

* usar contexto pré-carregado por execução;
* usar caches locais apenas durante a execução;
* evitar queries por candidato/turno;
* evitar queries por célula da grelha;
* evitar queries repetidas por atribuição no diagnóstico;
* não criar cache global;
* não criar migração ou índices novos nesta versão.

Estruturas relevantes:

* `GenerationContext` com mapas de militares, pertenças, referências, restrições e indisponibilidades;
* contexto interno do `MonthlyGridBuilder`;
* `DiagnosticContext` com mapas equivalentes para análise.

---

## 33-G. Estado implementado do PT na v1.3

A v1.3 introduz PT automático como serviço adicional de prioridade inferior.

Componentes:

* `PTGenerationOptions`;
* `AdditionalServiceGenerator`;
* campos opcionais de horário/duração em `Assignment`;
* validações específicas no `ScheduleDiagnosticService`;
* parâmetros PT no formulário de geração e regeneração.

Fluxo:

1. preservar atribuições existentes;
2. gerar AT/PO pela ordem obrigatória;
3. validar cobertura AT/PO do dia;
4. gerar PT apenas quando PT foi solicitado e AT/PO está completo;
5. persistir PT automático com horário/duração estruturados;
6. executar diagnóstico final.

Decisões:

* PT fica desligado por defeito;
* PT não conta para cobertura obrigatória;
* ausência de PT é informação, nunca erro;
* regra conservadora: não gerar PT num dia com AT/PO incompleto;
* PT automático antigo não é copiado na regeneração;
* PT manual é preservado e conta para limite diário;
* sem FF, FC, Ronda, CR, remunerados ou exportações nesta versão.

---

## 33-H. Estado implementado da FF na v1.4

A v1.4 introduz a gestão funcional inicial de FF por trabalho em feriado.

Componentes:

* `Holiday`;
* `HolidayLeaveCredit`;
* `HolidayLeaveCreditEvent`;
* `Assignment.holiday_leave_credit_id`;
* `app/services/holiday_credit_service.py`;
* `app/routes/holidays.py`;
* templates `holidays/*` e `ff/*`;
* validador FF no `ScheduleDiagnosticService`.

Fluxo:

1. registar feriados manualmente;
2. identificar atribuições elegíveis em feriados ativos;
3. criar crédito FF apenas por confirmação explícita ou versão consolidada;
4. preservar o código real no dia do feriado;
5. agendar FF numa versão `DRAFT` através de célula manual bloqueada;
6. preservar a ligação ao crédito em regeneração segura;
7. cancelar/reagendar/confirmar gozo através do serviço de FF;
8. diagnosticar incoerências sem corrigir automaticamente.

Decisões:

* não existem feriados pré-carregados;
* a origem do crédito é obrigatória e idempotente por atribuição;
* a FF não altera o ciclo `DS/DC`;
* a FF não é agendada em `DS/DC` nem sobre indisponibilidade ativa nesta versão;
* edição/limpeza genérica de célula FF ligada a crédito fica bloqueada;
* sem FC, Ronda, CR, remunerados ou exportações nesta versão.

---

## 33. Decisões que dependem de regras futuras

Alguns comportamentos só podem ser implementados automaticamente depois de serem formalizados no `ESCALA_RULES.md`.

Exemplos:

* forma de aquisição da FC;
* regras completas de Ronda;
* regras completas de CR;
* compensações da Ronda;
* regras do Serviço de Pronto;
* horários definitivos de todos os códigos;
* prioridade detalhada entre AT e PO;
* regras para recurso a SEC e SI;
* regras de distribuição por equipas;
* funcionamento dos serviços remunerados em simultâneo com serviços normais.

Até essas regras serem aprovadas, a aplicação deve permitir o registo manual, mas não inventar lógica automática.

---

## 34. Regra final da arquitetura

A arquitetura deve servir as regras operacionais e não o contrário.

Nenhum módulo técnico pode:

* alterar o ciclo;
* criar militares;
* ignorar restrições;
* eliminar alterações manuais;
* modificar prioridades;
* esconder conflitos;
* apagar histórico;
* tomar decisões operacionais não previstas.

Sempre que uma regra ainda não esteja definida, a aplicação deve:

1. evitar assumir um comportamento;
2. apresentar a situação ao Comandante;
3. permitir decisão manual;
4. registar a decisão;
5. aguardar formalização da regra antes de automatizar.

## Nota de Implementacao v1.6 - FC e FR

A implementacao atual acrescenta um modulo funcional de compensacoes sem recriar a aplicacao existente.

Componentes adicionados:

* `app/models/compensation.py` para modelos e enums de FC/FR;
* `app/services/compensation_service.py` para deteccao, confirmacao, agendamento, cancelamento, saldos e manutencao;
* `app/routes/compensations.py` para rotas de FC, FR e processamento de potenciais;
* `app/templates/compensations/` para paginas Jinja2 do modulo;
* comando CLI `flask process-compensations`;
* diagnostico FC/FR integrado em `ScheduleDiagnosticService`;
* preservacao de ligacoes FC/FR em regeneracao e versoes de correcao.

Regras arquiteturais mantidas:

* `FF`, `FC` e `FR` permanecem separados;
* rotas nao concentram regras operacionais;
* a manutencao de FC e idempotente e nao corre no arranque;
* versoes nao `DRAFT` nao recebem novos agendamentos FC/FR;
* nao foram criados dados demonstrativos ou ficticios.
