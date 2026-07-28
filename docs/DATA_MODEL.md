# Modelo de Dados — Escala de Serviço

**Projeto:** Escala de Serviço
**Documento:** `DATA_MODEL.md`
**Versão:** 1.0
**Estado:** Normativo
**Base de dados inicial:** SQLite
**ORM:** SQLAlchemy
**Migrações:** Alembic / Flask-Migrate
**Responsável funcional:** Comandante do Posto Territorial

---

## 1. Finalidade

Este documento define o modelo de dados da aplicação Escala de Serviço.

Estabelece:

* tabelas;
* campos;
* tipos de dados;
* relações;
* restrições;
* estados;
* índices;
* regras de integridade;
* regras de preservação histórica;
* políticas de eliminação;
* dados estruturais permitidos na instalação inicial.

O modelo deve suportar:

* gestão do efetivo;
* equipas operacionais;
* ciclo de folgas;
* restrições individuais;
* indisponibilidades;
* escalas mensais;
* versões da escala;
* nomeações;
* alterações manuais;
* diagnóstico;
* FF;
* FC;
* serviços remunerados;
* histórico;
* auditoria;
* utilizadores;
* exportações;
* cópias de segurança.

As regras operacionais encontram-se em:

```text
docs/ESCALA_RULES.md
```

A arquitetura técnica encontra-se em:

```text
docs/ARCHITECTURE.md
```

Em caso de conflito, prevalece o `ESCALA_RULES.md`.

---

## 2. Princípios gerais

O modelo de dados deve respeitar os seguintes princípios:

1. Nenhum militar fictício pode ser criado automaticamente.
2. Nenhuma equipa fictícia pode ser criada automaticamente.
3. A base de dados real nunca deve ser apagada e recriada para aplicar alterações.
4. Todas as mudanças estruturais devem utilizar migrações.
5. Dados históricos não devem ser eliminados quando um militar, equipa ou código deixa de estar ativo.
6. As alterações manuais devem ser preservadas e auditadas.
7. Uma escala publicada ou fechada deve manter as suas versões anteriores.
8. O ciclo de folgas deve possuir histórico de referências.
9. As FF devem possuir origem identificável.
10. Os serviços remunerados devem possuir histórico e razão da seleção.
11. As decisões automáticas devem poder ser explicadas.
12. As relações devem impedir eliminações em cascata perigosas.
13. Os dados de teste devem permanecer fora da base de dados real.
14. Datas, horas e valores booleanos devem utilizar tipos próprios.
15. Os códigos operacionais devem utilizar valores controlados.

---

## 3. Convenções de nomenclatura

### 3.1. Tabelas

As tabelas devem utilizar nomes em inglês, no plural e em `snake_case`.

Exemplos:

```text
militaries
teams
schedule_months
assignments
audit_logs
```

### 3.2. Campos

Os campos devem utilizar nomes em inglês e `snake_case`.

Exemplos:

```text
professional_number
reference_date
start_datetime
manual_override
created_at
```

### 3.3. Chaves primárias

Todas as tabelas principais devem possuir:

```text
id
```

Tipo recomendado:

```text
INTEGER
```

com incremento automático.

O número profissional de um militar não deve ser utilizado como chave primária.

### 3.4. Chaves estrangeiras

As chaves estrangeiras devem terminar em:

```text
_id
```

Exemplos:

```text
military_id
team_id
schedule_version_id
```

### 3.5. Datas de criação e atualização

Sempre que aplicável, as tabelas devem possuir:

```text
created_at
updated_at
```

As datas devem ser guardadas em UTC quando incluírem hora.

A interface pode apresentar as datas na hora local.

---

## 4. Tipos controlados

Os valores controlados devem ser implementados através de enums Python ou tabelas de configuração, conforme a necessidade.

Não devem existir múltiplas grafias para o mesmo valor.

Exemplo incorreto:

```text
Patrulheiro
PATRULHEIRO
patrulheiro
Patrulha
```

Exemplo correto:

```text
PATRULHEIRO
```

---

# PARTE I — UTILIZADORES E CONTROLO DE ACESSO

## 5. Tabela `users`

Representa os utilizadores autorizados a aceder à aplicação.

### Campos

| Campo           | Tipo         | Obrigatório | Descrição               |
| --------------- | ------------ | ----------: | ----------------------- |
| `id`            | INTEGER      |         Sim | Identificador interno   |
| `username`      | VARCHAR(80)  |         Sim | Nome de utilizador      |
| `full_name`     | VARCHAR(150) |         Sim | Nome completo           |
| `password_hash` | VARCHAR(255) |         Sim | Palavra-passe protegida |
| `role`          | VARCHAR(30)  |         Sim | Perfil do utilizador    |
| `active`        | BOOLEAN      |         Sim | Utilizador ativo        |
| `last_login_at` | DATETIME     |         Não | Último acesso           |
| `created_at`    | DATETIME     |         Sim | Data de criação         |
| `updated_at`    | DATETIME     |         Sim | Última alteração        |

### Perfis admitidos

```text
COMMANDER
EDITOR
VIEWER
```

### Restrições

* `username` deve ser único.
* A palavra-passe nunca pode ser guardada em texto simples.
* Um utilizador inativo não pode iniciar sessão.
* O último utilizador `COMMANDER` ativo não deve poder ser desativado sem confirmação especial.

### Índices

```text
UNIQUE(username)
INDEX(role)
INDEX(active)
```

---

# PARTE II — EFETIVO

## 6. Tabela `militaries`

Representa cada militar do efetivo.

### Campos

| Campo                 | Tipo         | Obrigatório | Descrição                            |
| --------------------- | ------------ | ----------: | ------------------------------------ |
| `id`                  | INTEGER      |         Sim | Identificador interno                |
| `professional_number` | VARCHAR(30)  |         Sim | Número profissional                  |
| `full_name`           | VARCHAR(180) |         Sim | Nome completo                        |
| `short_name`          | VARCHAR(100) |         Não | Nome abreviado para a escala         |
| `rank`                | VARCHAR(80)  |         Não | Posto ou categoria                   |
| `functional_group`    | VARCHAR(30)  |         Sim | Grupo funcional                      |
| `team_id`             | INTEGER      | Condicional | Equipa operacional                   |
| `start_date`          | DATE         |         Sim | Entrada no efetivo                   |
| `end_date`            | DATE         |         Não | Saída do efetivo                     |
| `active`              | BOOLEAN      |         Sim | Estado atual                         |
| `can_drive`           | BOOLEAN      |         Sim | Pode desempenhar funções de condutor |
| `notes`               | TEXT         |         Não | Observações                          |
| `created_by`          | INTEGER      |         Sim | Utilizador que criou                 |
| `created_at`          | DATETIME     |         Sim | Data de criação                      |
| `updated_at`          | DATETIME     |         Sim | Última alteração                     |

### Grupos funcionais admitidos

```text
PATRULHEIRO
SEC
SI
CMD
```

### Regras

* `professional_number` deve ser único.
* `full_name` não pode estar vazio.
* Um `PATRULHEIRO` ativo deve possuir `team_id`.
* SEC, SI e CMD não devem ser obrigados a possuir equipa operacional.
* `end_date` não pode ser anterior a `start_date`.
* Um militar não deve ser eliminado quando possuir histórico.
* A saída do efetivo deve ser representada através de `end_date` e `active = false`.
* Um militar inativo pode continuar visível nas escalas históricas.

### Implementação atual pós-v1.9

Na aplicação atual, a tabela `militaries` mantém compatibilidade histórica com o campo `name` e acrescenta:

* `first_name` para nome;
* `last_name` para sobrenome;
* `phone_number` para contacto telefónico português normalizado como texto;
* `is_paid_service_volunteer` para indicação informativa de voluntariado em serviços remunerados.

`Military.full_name` é a propriedade central de apresentação e usa `first_name` + `last_name`, recorrendo a `name` apenas como compatibilidade com registos legados.

O contacto telefónico não deve ser usado em grelhas de escala, diagnósticos, logs técnicos ou exportações operacionais Excel/PDF.

### Índices

```text
UNIQUE(professional_number)
INDEX(full_name)
INDEX(functional_group)
INDEX(team_id)
INDEX(active)
INDEX(start_date, end_date)
```

### Relações

```text
militaries.team_id → teams.id
militaries.created_by → users.id
```

---

## 7. Tabela `military_team_history`

Regista as mudanças de equipa dos militares.

### Campos

| Campo         | Tipo     | Obrigatório | Descrição           |
| ------------- | -------- | ----------: | ------------------- |
| `id`          | INTEGER  |         Sim | Identificador       |
| `military_id` | INTEGER  |         Sim | Militar             |
| `team_id`     | INTEGER  |         Sim | Equipa              |
| `valid_from`  | DATE     |         Sim | Data inicial        |
| `valid_until` | DATE     |         Não | Data final          |
| `reason`      | TEXT     |         Não | Motivo da alteração |
| `created_by`  | INTEGER  |         Sim | Utilizador          |
| `created_at`  | DATETIME |         Sim | Data do registo     |

### Regras

* Não podem existir períodos sobrepostos para o mesmo militar.
* Deve existir apenas uma equipa válida em cada data.
* Alterar a equipa atual não pode apagar o histórico anterior.
* A escala deve considerar a equipa válida na data concreta do serviço.

### Índices

```text
INDEX(military_id)
INDEX(team_id)
INDEX(valid_from, valid_until)
```

---

# PARTE III — EQUIPAS E CICLO DE FOLGAS

## 8. Tabela `teams`

Representa as equipas operacionais.

### Campos

| Campo           | Tipo        | Obrigatório | Descrição      |
| --------------- | ----------- | ----------: | -------------- |
| `id`            | INTEGER     |         Sim | Identificador  |
| `name`          | VARCHAR(80) |         Sim | Nome da equipa |
| `code`          | VARCHAR(20) |         Sim | Código curto   |
| `active`        | BOOLEAN     |         Sim | Estado         |
| `display_order` | INTEGER     |         Sim | Ordem visual   |
| `notes`         | TEXT        |         Não | Observações    |
| `created_by`    | INTEGER     |         Sim | Utilizador     |
| `created_at`    | DATETIME    |         Sim | Criação        |
| `updated_at`    | DATETIME    |         Sim | Alteração      |

### Regras

* `name` deve ser único.
* `code` deve ser único.
* Uma equipa não deve ser eliminada quando possuir militares, referências ou histórico.
* Equipas antigas devem ser desativadas.

### Índices

```text
UNIQUE(name)
UNIQUE(code)
INDEX(active)
INDEX(display_order)
```

---

## 9. Tabela `team_cycle_references`

Regista as referências utilizadas no cálculo do ciclo de folgas.

### Campos

| Campo             | Tipo     | Obrigatório | Descrição          |
| ----------------- | -------- | ----------: | ------------------ |
| `id`              | INTEGER  |         Sim | Identificador      |
| `team_id`         | INTEGER  |         Sim | Equipa             |
| `reference_date`  | DATE     |         Sim | Data de referência |
| `reference_phase` | INTEGER  |         Sim | Fase aplicável     |
| `valid_from`      | DATE     |         Sim | Início da validade |
| `valid_until`     | DATE     |         Não | Fim da validade    |
| `reason`          | TEXT     |         Não | Motivo             |
| `created_by`      | INTEGER  |         Sim | Utilizador         |
| `created_at`      | DATETIME |         Sim | Criação            |

### Valores de `reference_phase`

```text
1
2
3
4
5
6
```

### Regras

* `reference_phase` deve estar entre 1 e 6.
* Não podem existir referências sobrepostas para a mesma equipa.
* Deve existir apenas uma referência válida por equipa e data.
* Uma referência antiga nunca deve ser substituída sem preservação histórica.
* A alteração deve criar novo registo.
* A aplicação não pode alterar automaticamente uma referência.

### Índices

```text
INDEX(team_id)
INDEX(reference_date)
INDEX(valid_from, valid_until)
UNIQUE(team_id, valid_from)
```

---

## 10. Tabela `cycle_blocks`

Esta tabela é opcional e apenas deve existir caso seja necessário guardar blocos calculados.

Por defeito, os blocos devem ser calculados pelo `CycleCalculator`.

Caso sejam persistidos, devem ser tratados como resultado derivado e regenerável.

### Campos possíveis

| Campo                 | Tipo        | Obrigatório | Descrição             |
| --------------------- | ----------- | ----------: | --------------------- |
| `id`                  | INTEGER     |         Sim | Identificador         |
| `team_id`             | INTEGER     |         Sim | Equipa                |
| `phase`               | INTEGER     |         Sim | Fase                  |
| `block_start_date`    | DATE        |         Sim | Primeiro dia do bloco |
| `block_end_date`      | DATE        |         Sim | Último dia do bloco   |
| `reference_id`        | INTEGER     |         Sim | Referência utilizada  |
| `calculation_version` | VARCHAR(30) |         Sim | Versão do cálculo     |
| `created_at`          | DATETIME    |         Sim | Data de cálculo       |

### Regra

Esta tabela nunca pode ser considerada a fonte normativa do ciclo.

A fonte normativa continua a ser:

* referência da equipa;
* sequência prevista no `ESCALA_RULES.md`;
* implementação oficial do `CycleCalculator`.

---

# PARTE IV — CÓDIGOS E HORÁRIOS

## 11. Tabela `service_codes`

Representa os códigos utilizados na escala.

### Campos

| Campo                    | Tipo         | Obrigatório | Descrição                        |
| ------------------------ | ------------ | ----------: | -------------------------------- |
| `id`                     | INTEGER      |         Sim | Identificador                    |
| `code`                   | VARCHAR(20)  |         Sim | Código                           |
| `name`                   | VARCHAR(150) |         Sim | Designação                       |
| `category`               | VARCHAR(40)  |         Sim | Categoria                        |
| `priority`               | INTEGER      |         Sim | Prioridade                       |
| `required_staff`         | INTEGER      |         Sim | Efetivo mínimo                   |
| `active`                 | BOOLEAN      |         Sim | Estado                           |
| `is_primary`             | BOOLEAN      |         Sim | Pode ocupar a célula principal   |
| `can_overlap`            | BOOLEAN      |         Sim | Pode coexistir com outro registo |
| `counts_for_balance`     | BOOLEAN      |         Sim | Conta para equidade              |
| `allows_manual_override` | BOOLEAN      |         Sim | Permite força manual             |
| `display_order`          | INTEGER      |         Sim | Ordem visual                     |
| `background_color`       | VARCHAR(20)  |         Não | Cor                              |
| `text_color`             | VARCHAR(20)  |         Não | Cor do texto                     |
| `notes`                  | TEXT         |         Não | Observações                      |
| `created_at`             | DATETIME     |         Sim | Criação                          |
| `updated_at`             | DATETIME     |         Sim | Alteração                        |

### Categorias iniciais

```text
ATTENDANCE
PATROL
EXTRA_PATROL
REST
COMPENSATION
UNAVAILABILITY
COMMAND
ADMINISTRATIVE
REMUNERATED
OTHER
```

### Códigos estruturais iniciais

```text
AT1
AT2
AT3
PO1
PO2
PO3
PT
DS
DC
FF
FC
P
R
CR
SEC
SI
CMD
```

### Regras

* `code` deve ser único.
* Códigos utilizados historicamente não devem ser eliminados.
* Um código descontinuado deve passar para `active = false`.
* `required_staff` não pode ser negativo.
* A prioridade deve respeitar o `ESCALA_RULES.md`.
* Alterar o nome visual não deve alterar o código interno.

### Índices

```text
UNIQUE(code)
INDEX(category)
INDEX(active)
INDEX(priority)
```

---

## 12. Tabela `service_schedules`

Define horários associados aos códigos de serviço.

### Campos

| Campo              | Tipo         | Obrigatório | Descrição               |
| ------------------ | ------------ | ----------: | ----------------------- |
| `id`               | INTEGER      |         Sim | Identificador           |
| `service_code_id`  | INTEGER      |         Sim | Código                  |
| `name`             | VARCHAR(100) |         Sim | Nome do horário         |
| `start_time`       | TIME         |         Sim | Hora inicial            |
| `end_time`         | TIME         |         Sim | Hora final              |
| `crosses_midnight` | BOOLEAN      |         Sim | Termina no dia seguinte |
| `duration_minutes` | INTEGER      |         Não | Duração calculada       |
| `valid_from`       | DATE         |         Sim | Início da validade      |
| `valid_until`      | DATE         |         Não | Fim da validade         |
| `active`           | BOOLEAN      |         Sim | Estado                  |
| `created_by`       | INTEGER      |         Sim | Utilizador              |
| `created_at`       | DATETIME     |         Sim | Criação                 |

### Regras

* Não devem existir dois horários ativos sobrepostos para o mesmo código e período.
* O cálculo do descanso deve utilizar o horário válido na data do serviço.
* Os horários antigos devem ser preservados.

---

## 13. Tabela `service_code_compatibilities`

Define compatibilidades ou incompatibilidades entre códigos.

### Campos

| Campo                   | Tipo        | Obrigatório | Descrição       |
| ----------------------- | ----------- | ----------: | --------------- |
| `id`                    | INTEGER     |         Sim | Identificador   |
| `service_code_id`       | INTEGER     |         Sim | Primeiro código |
| `other_service_code_id` | INTEGER     |         Sim | Segundo código  |
| `compatibility_type`    | VARCHAR(30) |         Sim | Relação         |
| `notes`                 | TEXT        |         Não | Observações     |

### Valores possíveis

```text
COMPATIBLE
INCOMPATIBLE
REQUIRES_WARNING
```

### Regras

* Um código não pode ser relacionado consigo próprio.
* A relação deve ser única por par de códigos.
* As incompatibilidades não devem ser inventadas sem regra aprovada.

---

# PARTE V — RESTRIÇÕES E INDISPONIBILIDADES

## 14. Tabela `military_restrictions`

Representa restrições individuais.

### Campos

| Campo              | Tipo         | Obrigatório | Descrição            |
| ------------------ | ------------ | ----------: | -------------------- |
| `id`               | INTEGER      |         Sim | Identificador        |
| `military_id`      | INTEGER      |         Sim | Militar              |
| `restriction_type` | VARCHAR(50)  |         Sim | Tipo                 |
| `description`      | TEXT         |         Sim | Descrição            |
| `start_date`       | DATE         |         Sim | Início               |
| `end_date`         | DATE         |         Não | Fim                  |
| `start_time`       | TIME         |         Não | Limite inicial       |
| `end_time`         | TIME         |         Não | Limite final         |
| `weekdays`         | VARCHAR(30)  |         Não | Dias aplicáveis      |
| `active`           | BOOLEAN      |         Sim | Estado               |
| `forceable`        | BOOLEAN      |         Sim | Permite força manual |
| `source`           | VARCHAR(100) |         Não | Origem               |
| `notes`            | TEXT         |         Não | Observações          |
| `created_by`       | INTEGER      |         Sim | Utilizador           |
| `created_at`       | DATETIME     |         Sim | Criação              |
| `updated_at`       | DATETIME     |         Sim | Alteração            |

### Tipos iniciais

```text
ONLY_AT
NO_PT
NO_NIGHTS
NO_REMUNERATED
NO_ROUND
NO_DRIVING
MEDICAL_LIMITATION
TIME_LIMITATION
WEEKDAY_LIMITATION
OTHER
```

### Regras

* `end_date` não pode ser anterior a `start_date`.
* Restrições expiradas não devem ser eliminadas.
* Uma alteração manual pode ultrapassar uma restrição apenas mediante confirmação e auditoria.
* Limitações médicas devem ser apresentadas apenas a utilizadores autorizados.

### Índices

```text
INDEX(military_id)
INDEX(restriction_type)
INDEX(start_date, end_date)
INDEX(active)
```

---

## 15. Tabela `unavailabilities`

Representa férias, baixas, licenças e outras indisponibilidades.

### Campos

| Campo                 | Tipo        | Obrigatório | Descrição           |
| --------------------- | ----------- | ----------: | ------------------- |
| `id`                  | INTEGER     |         Sim | Identificador       |
| `military_id`         | INTEGER     |         Sim | Militar             |
| `unavailability_type` | VARCHAR(50) |         Sim | Tipo                |
| `start_datetime`      | DATETIME    |         Sim | Início              |
| `end_datetime`        | DATETIME    |         Sim | Fim                 |
| `display_code`        | VARCHAR(20) |         Não | Código visual       |
| `with_compensation`   | BOOLEAN     |         Sim | Origina compensação |
| `compensation_type`   | VARCHAR(30) |         Não | Tipo de compensação |
| `status`              | VARCHAR(30) |         Sim | Estado              |
| `notes`               | TEXT        |         Não | Observações         |
| `created_by`          | INTEGER     |         Sim | Utilizador          |
| `created_at`          | DATETIME    |         Sim | Criação             |
| `updated_at`          | DATETIME    |         Sim | Alteração           |
| `cancelled_at`        | DATETIME    |         Não | Cancelamento        |
| `cancelled_by`        | INTEGER     |         Não | Utilizador          |

### Tipos iniciais

```text
VACATION
MEDICAL_LEAVE
LICENSE
TRAINING
COURSE
COURT
DILIGENCE
DISPENSATION
AUTHORIZED_ABSENCE
OTHER
```

### Estados

```text
ACTIVE
CANCELLED
COMPLETED
```

### Regras

* `end_datetime` deve ser posterior a `start_datetime`.
* Indisponibilidades sobrepostas devem gerar aviso.
* Uma indisponibilidade cancelada deve permanecer no histórico.
* A geração automática não pode substituir uma indisponibilidade ativa.
* Uma força manual deve exigir confirmação e auditoria.

### Índices

```text
INDEX(military_id)
INDEX(unavailability_type)
INDEX(start_datetime, end_datetime)
INDEX(status)
```

---

# PARTE VI — ESCALA MENSAL

## 16. Tabela `schedule_months`

Representa cada mês de escala.

### Campos

| Campo                | Tipo        | Obrigatório | Descrição     |
| -------------------- | ----------- | ----------: | ------------- |
| `id`                 | INTEGER     |         Sim | Identificador |
| `year`               | INTEGER     |         Sim | Ano           |
| `month`              | INTEGER     |         Sim | Mês           |
| `status`             | VARCHAR(30) |         Sim | Estado        |
| `current_version_id` | INTEGER     |         Não | Versão atual  |
| `created_by`         | INTEGER     |         Sim | Utilizador    |
| `created_at`         | DATETIME    |         Sim | Criação       |
| `updated_at`         | DATETIME    |         Sim | Alteração     |
| `validated_at`       | DATETIME    |         Não | Validação     |
| `validated_by`       | INTEGER     |         Não | Utilizador    |
| `published_at`       | DATETIME    |         Não | Publicação    |
| `published_by`       | INTEGER     |         Não | Utilizador    |
| `closed_at`          | DATETIME    |         Não | Fecho         |
| `closed_by`          | INTEGER     |         Não | Utilizador    |
| `notes`              | TEXT        |         Não | Observações   |

### Estados

```text
NOT_GENERATED
DRAFT
VALIDATED
PUBLISHED
CLOSED
```

### Regras

* Deve existir apenas um registo principal por ano e mês.
* `month` deve estar entre 1 e 12.
* Uma escala com erros não autorizados não pode ser validada.
* Uma escala publicada ou fechada não deve ser alterada silenciosamente.
* A reabertura deve criar uma nova versão.

### Índices

```text
UNIQUE(year, month)
INDEX(status)
INDEX(current_version_id)
```

---

## 17. Tabela `schedule_versions`

Preserva as várias versões da escala mensal.

### Campos

| Campo                   | Tipo        | Obrigatório | Descrição             |
| ----------------------- | ----------- | ----------: | --------------------- |
| `id`                    | INTEGER     |         Sim | Identificador         |
| `schedule_month_id`     | INTEGER     |         Sim | Mês                   |
| `version_number`        | INTEGER     |         Sim | Número da versão      |
| `origin`                | VARCHAR(30) |         Sim | Origem                |
| `is_current`            | BOOLEAN     |         Sim | Versão atual          |
| `parent_version_id`     | INTEGER     |         Não | Versão anterior       |
| `generation_parameters` | JSON/TEXT   |         Não | Parâmetros utilizados |
| `notes`                 | TEXT        |         Não | Observações           |
| `created_by`            | INTEGER     |         Sim | Utilizador            |
| `created_at`            | DATETIME    |         Sim | Criação               |

### Origens

```text
INITIAL_GENERATION
REGENERATION
MANUAL_EDIT
VALIDATION
PUBLICATION
REOPENING
IMPORT
```

### Regras

* `version_number` deve ser único dentro do mês.
* Apenas uma versão deve possuir `is_current = true`.
* Uma versão publicada ou fechada nunca deve ser eliminada.
* A nova versão deve manter referência à anterior.
* Os parâmetros de geração devem permitir reproduzir ou explicar o resultado.

### Índices

```text
UNIQUE(schedule_month_id, version_number)
INDEX(schedule_month_id)
INDEX(is_current)
INDEX(parent_version_id)
```

---

## 18. Tabela `assignments`

Representa a nomeação principal diária de um militar.

### Campos

| Campo                  | Tipo        | Obrigatório | Descrição                |
| ---------------------- | ----------- | ----------: | ------------------------ |
| `id`                   | INTEGER     |         Sim | Identificador            |
| `schedule_version_id`  | INTEGER     |         Sim | Versão                   |
| `military_id`          | INTEGER     |         Sim | Militar                  |
| `assignment_date`      | DATE        |         Sim | Data                     |
| `service_code_id`      | INTEGER     |         Não | Código principal         |
| `service_schedule_id`  | INTEGER     |         Não | Horário                  |
| `start_datetime`       | DATETIME    |         Não | Início real              |
| `end_datetime`         | DATETIME    |         Não | Fim real                 |
| `origin`               | VARCHAR(30) |         Sim | Origem                   |
| `locked`               | BOOLEAN     |         Sim | Protegido de regeneração |
| `manual_override`      | BOOLEAN     |         Sim | Força manual             |
| `override_reason`      | TEXT        |         Não | Justificação             |
| `selection_reason`     | JSON/TEXT   |         Não | Razão automática         |
| `execution_status`     | VARCHAR(30) |         Sim | Estado de execução       |
| `source_assignment_id` | INTEGER     |         Não | Origem/substituição      |
| `created_by`           | INTEGER     |         Sim | Utilizador               |
| `created_at`           | DATETIME    |         Sim | Criação                  |
| `updated_at`           | DATETIME    |         Sim | Alteração                |

### Origens

```text
CYCLE
UNAVAILABILITY
HOLIDAY_CREDIT
COMPENSATION
AUTOMATIC_GENERATION
MANUAL_EDIT
IMPORT
SYSTEM
```

### Estados de execução

```text
PLANNED
EXECUTED
NOT_EXECUTED
REPLACED
CANCELLED
```

### Regras

* Deve existir apenas uma célula principal por militar, data e versão.
* `assignment_date` deve pertencer ao mês da escala.
* `start_datetime` e `end_datetime` devem ser coerentes com o horário.
* Uma célula manual deve possuir `locked = true`.
* Uma regeneração deve preservar células bloqueadas.
* Uma célula vazia pode ser representada com `service_code_id = null`.
* A origem deve ser sempre identificada.
* Uma nomeação automática deve guardar a razão de seleção quando possível.
* O código PT não pode satisfazer a cobertura de PO ou AT.

### Índices

```text
UNIQUE(schedule_version_id, military_id, assignment_date)
INDEX(schedule_version_id)
INDEX(military_id)
INDEX(assignment_date)
INDEX(service_code_id)
INDEX(locked)
INDEX(manual_override)
```

---

## 19. Tabela `additional_assignments`

Representa serviços adicionais que coexistam com a nomeação principal.

### Campos

| Campo                 | Tipo     | Obrigatório | Descrição          |
| --------------------- | -------- | ----------: | ------------------ |
| `id`                  | INTEGER  |         Sim | Identificador      |
| `assignment_id`       | INTEGER  |         Sim | Nomeação principal |
| `service_code_id`     | INTEGER  |         Sim | Código adicional   |
| `service_schedule_id` | INTEGER  |         Não | Horário            |
| `start_datetime`      | DATETIME |         Não | Início             |
| `end_datetime`        | DATETIME |         Não | Fim                |
| `manual_override`     | BOOLEAN  |         Sim | Força manual       |
| `notes`               | TEXT     |         Não | Observações        |
| `created_by`          | INTEGER  |         Sim | Utilizador         |
| `created_at`          | DATETIME |         Sim | Criação            |

### Regras

* Não deve ser utilizada para esconder incompatibilidades.
* Deve ser incluída no cálculo de descanso.
* Deve ser incluída no diagnóstico de sobreposição.
* Deve possuir código compatível ou violação autorizada.

---

## 20. Tabela `assignment_changes`

Regista as alterações efetuadas a uma célula da escala.

### Campos

| Campo                      | Tipo      | Obrigatório | Descrição           |
| -------------------------- | --------- | ----------: | ------------------- |
| `id`                       | INTEGER   |         Sim | Identificador       |
| `schedule_month_id`        | INTEGER   |         Sim | Mês                 |
| `schedule_version_id`      | INTEGER   |         Sim | Versão              |
| `assignment_id`            | INTEGER   |         Não | Nomeação            |
| `military_id`              | INTEGER   |         Sim | Militar             |
| `assignment_date`          | DATE      |         Sim | Data                |
| `previous_service_code_id` | INTEGER   |         Não | Código anterior     |
| `new_service_code_id`      | INTEGER   |         Não | Novo código         |
| `previous_start_datetime`  | DATETIME  |         Não | Horário anterior    |
| `new_start_datetime`       | DATETIME  |         Não | Novo horário        |
| `previous_end_datetime`    | DATETIME  |         Não | Horário anterior    |
| `new_end_datetime`         | DATETIME  |         Não | Novo horário        |
| `reason`                   | TEXT      |         Não | Justificação        |
| `warnings`                 | JSON/TEXT |         Não | Avisos apresentados |
| `confirmation_level`       | INTEGER   |         Sim | Confirmações        |
| `changed_by`               | INTEGER   |         Sim | Utilizador          |
| `created_at`               | DATETIME  |         Sim | Data                |

### Regras

* Cada edição manual deve criar um registo.
* Os valores anteriores e novos devem ser preservados.
* O registo não pode ser editado através da interface normal.
* A regeneração não pode apagar estes registos.

---

# PARTE VII — COBERTURA E DIAGNÓSTICO

## 21. Tabela `coverage_requirements`

Define o efetivo mínimo por código e período.

### Campos

| Campo             | Tipo     | Obrigatório | Descrição     |
| ----------------- | -------- | ----------: | ------------- |
| `id`              | INTEGER  |         Sim | Identificador |
| `service_code_id` | INTEGER  |         Sim | Código        |
| `required_staff`  | INTEGER  |         Sim | Mínimo        |
| `valid_from`      | DATE     |         Sim | Início        |
| `valid_until`     | DATE     |         Não | Fim           |
| `active`          | BOOLEAN  |         Sim | Estado        |
| `created_by`      | INTEGER  |         Sim | Utilizador    |
| `created_at`      | DATETIME |         Sim | Criação       |

### Configuração inicial

```text
AT1 = 1
AT2 = 1
AT3 = 1
PO1 = 2
PO2 = 2
PO3 = 2
```

### Regras

* A cobertura não pode ser alterada livremente sem autorização funcional.
* Alterações devem preservar histórico.
* A soma mínima inicial é de nove militares por dia.
* O PT não pode ser contabilizado como AT ou PO.

---

## 22. Tabela `diagnostic_issues`

Guarda os resultados do diagnóstico automático.

### Campos

| Campo                  | Tipo        | Obrigatório | Descrição           |
| ---------------------- | ----------- | ----------: | ------------------- |
| `id`                   | INTEGER     |         Sim | Identificador       |
| `schedule_version_id`  | INTEGER     |         Sim | Versão              |
| `military_id`          | INTEGER     |         Não | Militar             |
| `assignment_id`        | INTEGER     |         Não | Nomeação            |
| `assignment_date`      | DATE        |         Não | Data                |
| `validator_code`       | VARCHAR(80) |         Sim | Código do validador |
| `severity`             | VARCHAR(30) |         Sim | Gravidade           |
| `message`              | TEXT        |         Sim | Mensagem            |
| `details`              | JSON/TEXT   |         Não | Detalhes            |
| `authorized`           | BOOLEAN     |         Sim | Violação autorizada |
| `authorized_by`        | INTEGER     |         Não | Utilizador          |
| `authorized_at`        | DATETIME    |         Não | Data                |
| `authorization_reason` | TEXT        |         Não | Justificação        |
| `resolution_status`    | VARCHAR(30) |         Sim | Estado              |
| `resolved_at`          | DATETIME    |         Não | Resolução           |
| `created_at`           | DATETIME    |         Sim | Criação             |

### Gravidades

```text
ERROR
WARNING
INFO
AUTHORIZED_VIOLATION
```

### Estados de resolução

```text
OPEN
AUTHORIZED
RESOLVED
OBSOLETE
```

### Regras

* O diagnóstico não deve alterar a escala.
* Um erro autorizado deve manter a identificação da regra violada.
* Os diagnósticos antigos podem ser marcados como obsoletos após novo cálculo.
* Não devem ser apagados sem necessidade.

### Índices

```text
INDEX(schedule_version_id)
INDEX(military_id)
INDEX(assignment_date)
INDEX(validator_code)
INDEX(severity)
INDEX(resolution_status)
```

---

## 23. Tabela `generation_runs`

Regista cada execução do motor de geração.

### Campos

| Campo                 | Tipo        | Obrigatório | Descrição     |
| --------------------- | ----------- | ----------: | ------------- |
| `id`                  | INTEGER     |         Sim | Identificador |
| `schedule_month_id`   | INTEGER     |         Sim | Mês           |
| `schedule_version_id` | INTEGER     |         Não | Versão criada |
| `status`              | VARCHAR(30) |         Sim | Estado        |
| `generation_mode`     | VARCHAR(30) |         Sim | Modo          |
| `parameters`          | JSON/TEXT   |         Não | Parâmetros    |
| `started_at`          | DATETIME    |         Sim | Início        |
| `finished_at`         | DATETIME    |         Não | Fim           |
| `error_message`       | TEXT        |         Não | Erro          |
| `created_by`          | INTEGER     |         Sim | Utilizador    |

### Estados

```text
STARTED
COMPLETED
FAILED
CANCELLED
```

### Regras

* Uma geração falhada deve permanecer registada.
* Uma geração não deve ser marcada como concluída sem versão válida.
* Os parâmetros devem permitir compreender o que foi executado.
* Não deve conter dados pessoais desnecessários nos detalhes técnicos.

---

# PARTE VIII — HISTÓRICO E EQUIDADE

## 24. Tabela `service_history`

Representa o histórico acumulado por militar e serviço.

### Campos

| Campo                              | Tipo        | Obrigatório | Descrição     |
| ---------------------------------- | ----------- | ----------: | ------------- |
| `id`                               | INTEGER     |         Sim | Identificador |
| `military_id`                      | INTEGER     |         Sim | Militar       |
| `service_code_id`                  | INTEGER     |         Sim | Código        |
| `quantity`                         | INTEGER     |         Sim | Quantidade    |
| `history_type`                     | VARCHAR(30) |         Sim | Tipo          |
| `reference_date`                   | DATE        |         Não | Data          |
| `source_assignment_id`             | INTEGER     |         Não | Nomeação      |
| `source_remunerated_assignment_id` | INTEGER     |         Não | Remunerado    |
| `notes`                            | TEXT        |         Não | Observações   |
| `created_by`                       | INTEGER     |         Não | Utilizador    |
| `created_at`                       | DATETIME    |         Sim | Criação       |

### Tipos

```text
INITIAL
PLANNED
EXECUTED
MANUAL_ADJUSTMENT
IMPORTED
```

### Regras

* O histórico inicial deve ser separado do histórico gerado.
* A regeneração não pode duplicar contagens.
* Por defeito, a equidade deve considerar serviços confirmados ou definidos pela regra funcional.
* Ajustes manuais devem possuir justificação.
* Quantidades negativas apenas devem ser permitidas em ajustes controlados.

### Índices

```text
INDEX(military_id)
INDEX(service_code_id)
INDEX(history_type)
INDEX(reference_date)
```

---

## 25. Tabela `assignment_selection_details`

Guarda os critérios da seleção automática.

### Campos

| Campo                  | Tipo         | Obrigatório | Descrição             |
| ---------------------- | ------------ | ----------: | --------------------- |
| `id`                   | INTEGER      |         Sim | Identificador         |
| `assignment_id`        | INTEGER      |         Sim | Nomeação              |
| `selected_military_id` | INTEGER      |         Sim | Militar escolhido     |
| `candidate_snapshot`   | JSON/TEXT    |         Não | Candidatos analisados |
| `exclusion_reasons`    | JSON/TEXT    |         Não | Exclusões             |
| `ranking_criteria`     | JSON/TEXT    |         Não | Critérios             |
| `tie_breaker`          | VARCHAR(100) |         Não | Desempate             |
| `created_at`           | DATETIME     |         Sim | Criação               |

### Regra

Esta tabela deve permitir explicar por que determinado militar foi escolhido.

Não deve ser obrigatória para todas as células desde a primeira versão, mas a arquitetura deve estar preparada para a utilizar.

---

# PARTE IX — FF E COMPENSAÇÕES

## 26. Tabela `holiday_leave_credits`

Representa uma FF adquirida por trabalho num feriado.

### Campos

| Campo                     | Tipo        | Obrigatório | Descrição         |
| ------------------------- | ----------- | ----------: | ----------------- |
| `id`                      | INTEGER     |         Sim | Identificador     |
| `military_id`             | INTEGER     |         Sim | Militar           |
| `holiday_date`            | DATE        |         Sim | Feriado de origem |
| `source_assignment_id`    | INTEGER     |         Sim | Serviço executado |
| `service_code_id`         | INTEGER     |         Sim | Serviço prestado  |
| `acquired_at`             | DATETIME    |         Sim | Aquisição         |
| `status`                  | VARCHAR(30) |         Sim | Estado            |
| `scheduled_date`          | DATE        |         Não | Data prevista     |
| `used_date`               | DATE        |         Não | Data de gozo      |
| `scheduled_assignment_id` | INTEGER     |         Não | Célula FF         |
| `cancelled_at`            | DATETIME    |         Não | Cancelamento      |
| `cancelled_by`            | INTEGER     |         Não | Utilizador        |
| `cancellation_reason`     | TEXT        |         Não | Justificação      |
| `notes`                   | TEXT        |         Não | Observações       |
| `created_by`              | INTEGER     |         Sim | Utilizador        |
| `scheduled_by`            | INTEGER     |         Não | Utilizador        |
| `created_at`              | DATETIME    |         Sim | Criação           |
| `updated_at`              | DATETIME    |         Sim | Alteração         |

### Estados

```text
PENDING
SCHEDULED
USED
RESCHEDULED
CANCELLED
```

### Regras

* Uma FF apenas pode ser criada quando exista trabalho efetivamente prestado num feriado.
* A FF não pode ser duplicada.
* A FF pendente não ocupa célula da escala.
* A FF agendada deve estar ligada à célula correspondente.
* A FF não altera o ciclo DS/DC.
* Uma FF cancelada permanece no histórico.
* A marcação deve respeitar disponibilidade operacional.
* O Cmdt pode forçar a marcação mediante aviso e auditoria.

### Restrição de unicidade

Recomendação:

```text
UNIQUE(military_id, holiday_date, source_assignment_id)
```

### Índices

```text
INDEX(military_id)
INDEX(holiday_date)
INDEX(status)
INDEX(scheduled_date)
```

---

## 27. Tabela `holiday_leave_credit_events`

Regista todas as alterações de estado de uma FF.

### Campos

| Campo                     | Tipo        | Obrigatório | Descrição       |
| ------------------------- | ----------- | ----------: | --------------- |
| `id`                      | INTEGER     |         Sim | Identificador   |
| `holiday_leave_credit_id` | INTEGER     |         Sim | FF              |
| `event_type`              | VARCHAR(30) |         Sim | Evento          |
| `previous_status`         | VARCHAR(30) |         Não | Estado anterior |
| `new_status`              | VARCHAR(30) |         Sim | Novo estado     |
| `previous_date`           | DATE        |         Não | Data anterior   |
| `new_date`                | DATE        |         Não | Nova data       |
| `reason`                  | TEXT        |         Não | Motivo          |
| `created_by`              | INTEGER     |         Sim | Utilizador      |
| `created_at`              | DATETIME    |         Sim | Data            |

### Eventos

```text
CREATED
SCHEDULED
RESCHEDULED
USED
CANCELLED
REOPENED
```

---

## 28. Tabela `compensation_credits`

Representa outras compensações, incluindo FC, quando as respetivas regras forem formalizadas.

### Campos

| Campo               | Tipo        | Obrigatório | Descrição         |
| ------------------- | ----------- | ----------: | ----------------- |
| `id`                | INTEGER     |         Sim | Identificador     |
| `military_id`       | INTEGER     |         Sim | Militar           |
| `compensation_type` | VARCHAR(30) |         Sim | Tipo              |
| `source_type`       | VARCHAR(50) |         Sim | Origem            |
| `source_id`         | INTEGER     |         Não | Registo de origem |
| `acquired_date`     | DATE        |         Sim | Aquisição         |
| `status`            | VARCHAR(30) |         Sim | Estado            |
| `scheduled_date`    | DATE        |         Não | Agendamento       |
| `used_date`         | DATE        |         Não | Gozo              |
| `notes`             | TEXT        |         Não | Observações       |
| `created_by`        | INTEGER     |         Sim | Utilizador        |
| `created_at`        | DATETIME    |         Sim | Criação           |
| `updated_at`        | DATETIME    |         Sim | Alteração         |

### Regra

A lógica automática de aquisição de FC não deve ser implementada até estar formalmente definida no `ESCALA_RULES.md`.

---

# PARTE X — FERIADOS

## 29. Tabela `holidays`

Representa os feriados reconhecidos pela aplicação.

### Campos

| Campo          | Tipo         | Obrigatório | Descrição     |
| -------------- | ------------ | ----------: | ------------- |
| `id`           | INTEGER      |         Sim | Identificador |
| `holiday_date` | DATE         |         Sim | Data          |
| `name`         | VARCHAR(150) |         Sim | Designação    |
| `holiday_type` | VARCHAR(30)  |         Sim | Tipo          |
| `active`       | BOOLEAN      |         Sim | Estado        |
| `notes`        | TEXT         |         Não | Observações   |
| `created_by`   | INTEGER      |         Sim | Utilizador    |
| `created_at`   | DATETIME     |         Sim | Criação       |

### Tipos

```text
NATIONAL
MUNICIPAL
INSTITUTIONAL
OTHER
```

### Regras

* `holiday_date` e tipo devem impedir duplicações.
* A aplicação deve distinguir feriados nacionais e locais.
* A criação de FF deve consultar esta tabela.
* A alteração de um feriado não pode apagar FF já adquiridas.

### Índices

```text
UNIQUE(holiday_date, holiday_type)
INDEX(holiday_date)
INDEX(active)
```

---

# PARTE XI — SERVIÇOS REMUNERADOS

## 30. Tabela `remunerated_preferences`

Representa as preferências individuais.

### Campos

| Campo                    | Tipo     | Obrigatório | Descrição           |
| ------------------------ | -------- | ----------: | ------------------- |
| `id`                     | INTEGER  |         Sim | Identificador       |
| `military_id`            | INTEGER  |         Sim | Militar             |
| `volunteer`              | BOOLEAN  |         Sim | Voluntário          |
| `volunteer_on_days_off`  | BOOLEAN  |         Sim | Voluntário em folga |
| `waives_eight_hour_rest` | BOOLEAN  |         Sim | Abdica do descanso  |
| `valid_from`             | DATE     |         Sim | Início              |
| `valid_until`            | DATE     |         Não | Fim                 |
| `notes`                  | TEXT     |         Não | Observações         |
| `created_by`             | INTEGER  |         Sim | Utilizador          |
| `created_at`             | DATETIME |         Sim | Criação             |

### Regras

* As preferências devem possuir validade temporal.
* Não deve existir mais de uma preferência ativa para o mesmo período.
* Abdicar das oito horas deve ficar registado de forma explícita.
* A preferência não substitui a decisão de comando.

---

## 31. Tabela `remunerated_assignments`

Representa cada serviço remunerado.

### Campos

| Campo                    | Tipo        | Obrigatório | Descrição            |
| ------------------------ | ----------- | ----------: | -------------------- |
| `id`                     | INTEGER     |         Sim | Identificador        |
| `military_id`            | INTEGER     |         Sim | Militar              |
| `table_type`             | VARCHAR(20) |         Sim | Tabela               |
| `service_date`           | DATE        |         Sim | Data                 |
| `start_datetime`         | DATETIME    |         Sim | Início               |
| `end_datetime`           | DATETIME    |         Sim | Fim                  |
| `status`                 | VARCHAR(30) |         Sim | Estado               |
| `selection_reason`       | JSON/TEXT   |         Não | Razão                |
| `non_volunteer_override` | BOOLEAN     |         Sim | Não voluntário       |
| `first_confirmation_by`  | INTEGER     |         Não | Primeira confirmação |
| `first_confirmation_at`  | DATETIME    |         Não | Data                 |
| `second_confirmation_by` | INTEGER     |         Não | Segunda confirmação  |
| `second_confirmation_at` | DATETIME    |         Não | Data                 |
| `notes`                  | TEXT        |         Não | Observações          |
| `created_by`             | INTEGER     |         Sim | Utilizador           |
| `created_at`             | DATETIME    |         Sim | Criação              |
| `updated_at`             | DATETIME    |         Sim | Alteração            |

### Tipos

```text
TABLE_A
TABLE_B
```

### Estados

```text
PLANNED
CONFIRMED
EXECUTED
CANCELLED
REPLACED
```

### Regras

* Nomear não voluntário exige dupla confirmação.
* O cálculo de descanso deve considerar o serviço.
* Os totais devem distinguir Tabela A e Tabela B.
* A seleção deve respeitar a ordem definida no `ESCALA_RULES.md`.
* O resultado deve ser determinístico.

### Índices

```text
INDEX(military_id)
INDEX(table_type)
INDEX(service_date)
INDEX(status)
```

---

## 32. Tabela `remunerated_selection_candidates`

Regista os candidatos avaliados numa seleção de remunerados.

### Campos

| Campo                       | Tipo     | Obrigatório | Descrição      |
| --------------------------- | -------- | ----------: | -------------- |
| `id`                        | INTEGER  |         Sim | Identificador  |
| `remunerated_assignment_id` | INTEGER  |         Sim | Serviço        |
| `military_id`               | INTEGER  |         Sim | Candidato      |
| `eligible`                  | BOOLEAN  |         Sim | Elegível       |
| `exclusion_reason`          | TEXT     |         Não | Exclusão       |
| `table_b_total`             | INTEGER  |         Sim | Total Tabela B |
| `total_remunerated`         | INTEGER  |         Sim | Total global   |
| `last_remunerated_date`     | DATE     |         Não | Último         |
| `ranking_position`          | INTEGER  |         Não | Posição        |
| `created_at`                | DATETIME |         Sim | Criação        |

### Regra

Esta tabela deve permitir reconstruir a ordem de escolha.

---

# PARTE XII — RONDA, CR E PRONTO

## 33. Tabela `special_services`

Representa serviços especiais cuja lógica possa exigir mais de um participante.

### Campos

| Campo            | Tipo        | Obrigatório | Descrição     |
| ---------------- | ----------- | ----------: | ------------- |
| `id`             | INTEGER     |         Sim | Identificador |
| `service_type`   | VARCHAR(30) |         Sim | Tipo          |
| `service_date`   | DATE        |         Sim | Data          |
| `start_datetime` | DATETIME    |         Não | Início        |
| `end_datetime`   | DATETIME    |         Não | Fim           |
| `status`         | VARCHAR(30) |         Sim | Estado        |
| `notes`          | TEXT        |         Não | Observações   |
| `created_by`     | INTEGER     |         Sim | Utilizador    |
| `created_at`     | DATETIME    |         Sim | Criação       |

### Tipos iniciais

```text
ROUND
READY_SERVICE
OTHER
```

### Regra

A lógica automática de Ronda, CR e P apenas deve ser implementada depois de formalizadas todas as regras.

---

## 34. Tabela `special_service_members`

Liga os militares aos serviços especiais.

### Campos

| Campo                | Tipo        | Obrigatório | Descrição        |
| -------------------- | ----------- | ----------: | ---------------- |
| `id`                 | INTEGER     |         Sim | Identificador    |
| `special_service_id` | INTEGER     |         Sim | Serviço          |
| `military_id`        | INTEGER     |         Sim | Militar          |
| `role_code`          | VARCHAR(20) |         Sim | Função           |
| `assignment_id`      | INTEGER     |         Não | Célula da escala |
| `manual_override`    | BOOLEAN     |         Sim | Força manual     |
| `notes`              | TEXT        |         Não | Observações      |
| `created_by`         | INTEGER     |         Sim | Utilizador       |
| `created_at`         | DATETIME    |         Sim | Criação          |

### Funções possíveis

```text
R
CR
P
```

---

# PARTE XIII — AUDITORIA

## 35. Tabela `audit_logs`

Regista todas as ações funcionais relevantes.

### Campos

| Campo                | Tipo        | Obrigatório | Descrição        |
| -------------------- | ----------- | ----------: | ---------------- |
| `id`                 | INTEGER     |         Sim | Identificador    |
| `user_id`            | INTEGER     |         Não | Utilizador       |
| `action`             | VARCHAR(80) |         Sim | Ação             |
| `entity_type`        | VARCHAR(80) |         Sim | Tipo da entidade |
| `entity_id`          | INTEGER     |         Não | Identificador    |
| `schedule_month_id`  | INTEGER     |         Não | Mês afetado      |
| `previous_value`     | JSON/TEXT   |         Não | Valor anterior   |
| `new_value`          | JSON/TEXT   |         Não | Valor novo       |
| `reason`             | TEXT        |         Não | Justificação     |
| `warnings`           | JSON/TEXT   |         Não | Avisos           |
| `confirmation_level` | INTEGER     |         Sim | Confirmações     |
| `ip_address`         | VARCHAR(50) |         Não | Endereço local   |
| `created_at`         | DATETIME    |         Sim | Data             |

### Ações iniciais

```text
CREATE
UPDATE
DEACTIVATE
REACTIVATE
DELETE
GENERATE
REGENERATE
VALIDATE
PUBLISH
CLOSE
REOPEN
MANUAL_OVERRIDE
AUTHORIZE_VIOLATION
CREATE_BACKUP
RESTORE_BACKUP
EXPORT
LOGIN
LOGOUT
```

### Regras

* Os registos não devem ser editáveis.
* Não devem ser eliminados por operações normais.
* Dados sensíveis devem ser minimizados.
* A auditoria não substitui logs técnicos.

### Índices

```text
INDEX(user_id)
INDEX(action)
INDEX(entity_type, entity_id)
INDEX(schedule_month_id)
INDEX(created_at)
```

---

# PARTE XIV — EXPORTAÇÕES E BACKUPS

## 36. Tabela `export_records`

Regista as exportações produzidas.

### Campos

| Campo                 | Tipo         | Obrigatório | Descrição     |
| --------------------- | ------------ | ----------: | ------------- |
| `id`                  | INTEGER      |         Sim | Identificador |
| `schedule_month_id`   | INTEGER      |         Sim | Mês           |
| `schedule_version_id` | INTEGER      |         Sim | Versão        |
| `export_type`         | VARCHAR(20)  |         Sim | Formato       |
| `file_name`           | VARCHAR(255) |         Sim | Nome          |
| `file_path`           | VARCHAR(500) |         Não | Caminho       |
| `file_hash`           | VARCHAR(128) |         Não | Verificação   |
| `created_by`          | INTEGER      |         Sim | Utilizador    |
| `created_at`          | DATETIME     |         Sim | Criação       |

### Formatos

```text
PDF
XLSX
CSV
```

### Regras

* A exportação deve indicar a versão utilizada.
* A exportação não pode alterar a escala.
* O caminho não deve permitir acesso fora da pasta autorizada.
* O ficheiro pode ser eliminado mantendo o registo histórico.

---

## 37. Tabela `backup_records`

Regista os backups efetuados.

### Campos

| Campo         | Tipo         | Obrigatório | Descrição     |
| ------------- | ------------ | ----------: | ------------- |
| `id`          | INTEGER      |         Sim | Identificador |
| `file_name`   | VARCHAR(255) |         Sim | Nome          |
| `file_path`   | VARCHAR(500) |         Sim | Caminho       |
| `file_size`   | INTEGER      |         Não | Tamanho       |
| `file_hash`   | VARCHAR(128) |         Não | Integridade   |
| `backup_type` | VARCHAR(30)  |         Sim | Tipo          |
| `status`      | VARCHAR(30)  |         Sim | Estado        |
| `created_by`  | INTEGER      |         Sim | Utilizador    |
| `created_at`  | DATETIME     |         Sim | Criação       |
| `verified_at` | DATETIME     |         Não | Verificação   |
| `notes`       | TEXT         |         Não | Observações   |

### Tipos

```text
MANUAL
PRE_MIGRATION
PRE_RESTORE
PRE_IMPORT
PRE_DESTRUCTIVE_OPERATION
```

### Estados

```text
CREATED
VERIFIED
FAILED
RESTORED
```

---

# PARTE XV — CONFIGURAÇÃO

## 38. Tabela `application_settings`

Guarda configurações controladas.

### Campos

| Campo              | Tipo         | Obrigatório | Descrição         |
| ------------------ | ------------ | ----------: | ----------------- |
| `id`               | INTEGER      |         Sim | Identificador     |
| `setting_key`      | VARCHAR(100) |         Sim | Chave             |
| `setting_value`    | TEXT         |         Não | Valor             |
| `value_type`       | VARCHAR(30)  |         Sim | Tipo              |
| `category`         | VARCHAR(50)  |         Sim | Categoria         |
| `editable`         | BOOLEAN      |         Sim | Pode ser alterada |
| `requires_restart` | BOOLEAN      |         Sim | Exige reinício    |
| `description`      | TEXT         |         Não | Descrição         |
| `updated_by`       | INTEGER      |         Não | Utilizador        |
| `updated_at`       | DATETIME     |         Sim | Alteração         |

### Tipos

```text
STRING
INTEGER
BOOLEAN
DATE
TIME
JSON
```

### Regras

* Regras estruturais não devem ser livremente editáveis.
* Alterações relevantes devem ficar em auditoria.
* Segredos não devem ser guardados nesta tabela em texto simples.

---

# PARTE XVI — RELAÇÕES PRINCIPAIS

## 39. Diagrama lógico simplificado

```text
users
 ├── militaries.created_by
 ├── teams.created_by
 ├── schedule_months.created_by
 ├── assignments.created_by
 └── audit_logs.user_id

teams
 ├── militaries.team_id
 ├── military_team_history.team_id
 └── team_cycle_references.team_id

militaries
 ├── military_team_history
 ├── military_restrictions
 ├── unavailabilities
 ├── assignments
 ├── service_history
 ├── holiday_leave_credits
 ├── remunerated_preferences
 └── remunerated_assignments

schedule_months
 ├── schedule_versions
 ├── diagnostic_issues
 ├── generation_runs
 ├── audit_logs
 └── export_records

schedule_versions
 ├── assignments
 └── diagnostic_issues

assignments
 ├── additional_assignments
 ├── assignment_changes
 ├── assignment_selection_details
 └── holiday_leave_credits

service_codes
 ├── service_schedules
 ├── assignments
 ├── additional_assignments
 ├── service_history
 ├── coverage_requirements
 └── remunerated_assignments
```

---

# PARTE XVII — POLÍTICA DE ELIMINAÇÃO

## 40. Eliminação lógica

Devem ser desativados, em vez de eliminados:

* militares;
* equipas;
* utilizadores;
* códigos;
* horários;
* restrições;
* configurações estruturais.

### Campos recomendados

```text
active
end_date
valid_until
status
```

---

## 41. Eliminação definitiva

A eliminação definitiva só deve ser permitida quando:

* o registo foi criado por erro;
* não possui relações históricas;
* não participa em nenhuma escala;
* não possui auditoria relevante;
* existe confirmação explícita.

A eliminação de um militar nunca deve apagar:

* escalas;
* histórico;
* FF;
* remunerados;
* auditoria;
* alterações manuais.

---

## 42. Regras de chaves estrangeiras

Por defeito, deve utilizar-se:

```text
ON DELETE RESTRICT
```

ou comportamento equivalente no ORM.

Pode utilizar-se:

```text
ON DELETE SET NULL
```

quando o histórico possa permanecer sem a entidade atual.

A eliminação em cascata apenas deve ser utilizada para entidades secundárias sem valor histórico próprio.

Exemplos possíveis:

* detalhes temporários de uma geração cancelada;
* candidatos de uma seleção eliminada antes de confirmação;
* itens técnicos sem valor funcional.

Não utilizar cascata sobre:

* assignments;
* schedule_versions;
* audit_logs;
* service_history;
* holiday_leave_credits;
* remunerated_assignments.

---

# PARTE XVIII — INTEGRIDADE E VALIDAÇÃO

## 43. Restrições mínimas

A base de dados deve garantir, sempre que possível:

```text
professional_number único
team code único
service code único
um mês por ano/mês
uma célula por militar/data/versão
uma versão por número dentro do mês
uma FF por origem
fases apenas entre 1 e 6
meses apenas entre 1 e 12
datas finais posteriores às iniciais
quantidades mínimas não negativas
```

---

## 44. Validação na aplicação

Nem todas as regras podem ser implementadas apenas na base de dados.

Devem ser validadas pelos serviços:

* continuidade do ciclo;
* descanso mínimo;
* cobertura diária;
* restrições;
* indisponibilidades;
* compatibilidade;
* distribuição equilibrada;
* prioridade dos códigos;
* seleção de remunerados;
* disponibilidade para FF;
* alterações manuais.

A base de dados deve proteger a estrutura.

Os serviços devem proteger as regras operacionais.

---

# PARTE XIX — DADOS INICIAIS

## 45. Dados permitidos

Na primeira instalação podem ser criados:

* utilizador administrador;
* códigos oficiais;
* categorias;
* tipos de restrição;
* tipos de indisponibilidade;
* estados;
* cobertura mínima;
* configurações essenciais.

---

## 46. Dados proibidos

Não podem ser criados automaticamente:

* militares;
* equipas A, B, C, D ou E sem ação do utilizador;
* escalas;
* indisponibilidades;
* restrições pessoais;
* histórico;
* FF;
* FC;
* remunerados;
* dados de demonstração.

Mesmo que normalmente existam cinco equipas, estas devem ser criadas ou confirmadas pelo utilizador.

---

# PARTE XX — MIGRAÇÕES

## 47. Regras para criação das tabelas

A implementação deve ser feita por fases.

Ordem recomendada:

### Migração 1 — Base

* `users`;
* `teams`;
* `militaries`;
* `military_team_history`;
* `team_cycle_references`.

### Migração 2 — Configuração operacional

* `service_codes`;
* `service_schedules`;
* `coverage_requirements`;
* `holidays`.

### Migração 3 — Restrições

* `military_restrictions`;
* `unavailabilities`.

### Migração 4 — Escala

* `schedule_months`;
* `schedule_versions`;
* `assignments`;
* `additional_assignments`.

### Migração 5 — Diagnóstico e alterações

* `assignment_changes`;
* `diagnostic_issues`;
* `generation_runs`.

### Migração 6 — Histórico e equidade

* `service_history`;
* `assignment_selection_details`.

### Migração 7 — FF e compensações

* `holiday_leave_credits`;
* `holiday_leave_credit_events`;
* `compensation_credits`.

### Migração 8 — Remunerados

* `remunerated_preferences`;
* `remunerated_assignments`;
* `remunerated_selection_candidates`.

### Migração 9 — Serviços especiais

* `special_services`;
* `special_service_members`.

### Migração 10 — Auditoria e suporte

* `audit_logs`;
* `export_records`;
* `backup_records`;
* `application_settings`.

A ordem pode ser ajustada tecnicamente, desde que preserve relações e segurança.

---

# PARTE XX-A — ESTADO IMPLEMENTADO NA v0.7

## 47-A. Tabelas criadas na v0.7

A v0.7 criou apenas as tabelas:

* `schedule_months`;
* `schedule_versions`.

Campos principais de `schedule_months`:

* `id`;
* `year`;
* `month`;
* `status`;
* `created_at`;
* `updated_at`.

Restrições:

* combinação única `year` + `month`;
* `month` entre 1 e 12;
* `year` entre 2000 e 2100;
* `status` limitado a `NOT_GENERATED`, `DRAFT`, `VALIDATED`, `PUBLISHED` e `CLOSED`.

Campos principais de `schedule_versions`:

* `id`;
* `schedule_month_id`;
* `version_number`;
* `status`;
* `source`;
* `description`;
* `created_at`;
* `updated_at`.

Restrições:

* `schedule_month_id` referencia `schedule_months.id`;
* `version_number` é único dentro do mês;
* `version_number` deve ser maior ou igual a 1;
* `source` limitado a `INITIAL`, `MANUAL` e `SYSTEM`.

Decisão da v0.7:

* não foi criada tabela de atribuições ou células persistidas;
* a grelha é calculada dinamicamente a partir das fontes de verdade já existentes;
* a tabela de células/atribuições só deve ser criada quando a edição manual ou geração operacional justificar persistência.

---

# PARTE XX-B — ESTADO IMPLEMENTADO NA v0.8

## 47-B. Tabelas criadas na v0.8

A v0.8 criou apenas as tabelas:

* `assignments`;
* `assignment_changes`.

Campos principais de `assignments`:

* `id`;
* `schedule_version_id`;
* `military_id`;
* `assignment_date`;
* `code`;
* `source`;
* `is_manual`;
* `is_locked`;
* `has_override`;
* `override_reason`;
* `notes`;
* `is_cleared`;
* `created_at`;
* `updated_at`.

Restrições:

* combinação única de `schedule_version_id`, `military_id` e `assignment_date`;
* `schedule_version_id` referencia `schedule_versions.id`;
* `military_id` referencia `militaries.id`;
* `source` limitado a `MANUAL`, `SYSTEM` e `IMPORTED`;
* `code` limitado ao catálogo oficial implementado;
* quando `is_cleared` é verdadeiro, `code` deve ser nulo;
* quando `is_cleared` é falso, `code` deve estar preenchido.

Campos principais de `assignment_changes`:

* `id`;
* `assignment_id`;
* `change_type`;
* `previous_code`;
* `new_code`;
* `previous_locked`;
* `new_locked`;
* `previous_override`;
* `new_override`;
* `reason`;
* `created_at`.

Tipos de alteração:

* `CREATED`;
* `UPDATED`;
* `CLEARED`;
* `LOCKED`;
* `UNLOCKED`;
* `OVERRIDE_APPLIED`;
* `OVERRIDE_REMOVED`.

Decisão da v0.8:

* limpar uma célula não elimina fisicamente o registo de atribuição;
* a preservação é feita por `is_cleared` e pelo histórico associado;
* autenticação e `user_id` continuam pendentes para fase futura.

---

# PARTE XX-C — ESTADO IMPLEMENTADO NA v0.9

## 47-C. Tabelas criadas na v0.9

A v0.9 criou apenas as tabelas:

* `diagnostic_runs`;
* `diagnostic_issues`.

Campos principais de `diagnostic_runs`:

* `id`;
* `schedule_version_id`;
* `started_at`;
* `completed_at`;
* `status`;
* `total_errors`;
* `total_warnings`;
* `total_infos`;
* `created_at`.

Estados:

* `RUNNING`;
* `COMPLETED`;
* `FAILED`.

Campos principais de `diagnostic_issues`:

* `id`;
* `diagnostic_run_id`;
* `level`;
* `category`;
* `code`;
* `title`;
* `description`;
* `assignment_date`;
* `military_id`;
* `team_id`;
* `assignment_id`;
* `is_blocking`;
* `suggested_action`;
* `details_json`;
* `created_at`.

Níveis:

* `ERROR`;
* `WARNING`;
* `INFO`.

Decisão da v0.9:

* diagnósticos são históricos e não são apagados por nova execução;
* `details_json` guarda detalhe técnico estruturado;
* o diagnóstico não corrige dados nem executa geração.

---

# PARTE XXI — TESTES DO MODELO

## 48. Testes obrigatórios

Devem existir testes para confirmar:

1. não é possível criar dois militares com o mesmo número profissional;
2. um patrulheiro ativo exige equipa;
3. não existem referências de ciclo sobrepostas;
4. a fase apenas aceita valores de 1 a 6;
5. não é possível criar dois meses iguais;
6. não existem duas células para o mesmo militar, data e versão;
7. uma FF não pode ser duplicada;
8. uma escala histórica permanece após desativar um militar;
9. a eliminação de uma equipa com histórico é impedida;
10. uma versão publicada não é eliminada;
11. as alterações manuais permanecem registadas;
12. os horários que atravessam a meia-noite são válidos;
13. uma indisponibilidade inválida é rejeitada;
14. um serviço remunerado não voluntário exige dupla confirmação;
15. a base de testes não cria militares automaticamente.

---

# PARTE XX-C — ESTADO IMPLEMENTADO NA v1.0

## 49-C. Tabelas criadas na v1.0

A v1.0 criou apenas as tabelas:

```text
generation_runs
assignment_selection_details
```

## 50-C. generation_runs

Campos principais:

```text
id
schedule_version_id
diagnostic_run_id
status
started_at
completed_at
total_created
total_preserved_manual
total_unfilled
total_warnings
parameters_json
summary_json
created_at
```

Estados:

```text
RUNNING
COMPLETED
COMPLETED_WITH_WARNINGS
FAILED
```

## 51-C. assignment_selection_details

Campos principais:

```text
id
generation_run_id
assignment_date
service_code
military_id
is_eligible
is_selected
reason
position
metrics_json
created_at
```

`service_code` está limitado a:

```text
AT1
AT2
AT3
PO1
PO2
PO3
```

## 52-C. Decisões da v1.0

* A geração cria atribuições na tabela `assignments`.
* Atribuições automáticas usam `source=SYSTEM`, `is_manual=False`, `is_locked=False` e `has_override=False`.
* Cada atribuição automática cria um `AssignmentChange` do tipo `CREATED`.
* A geração preserva atribuições manuais existentes.
* A geração não cria PT, FF, FC, Ronda, CR ou remunerados.
* A geração não insere dados fictícios.

---

# PARTE XX-D — ESTADO IMPLEMENTADO NA v1.1

## 53-D. Campos acrescentados em schedule_versions

```text
parent_version_id
generation_mode
```

`parent_version_id` aponta para a versão de origem quando a versão resulta de regeneração.

`generation_mode` aceita:

```text
FILL_EMPTY
REGENERATE_AUTOMATIC
```

## 54-D. Campos acrescentados em generation_runs

```text
generation_mode
source_version_id
result_version_id
```

Estes campos permitem distinguir execuções de preenchimento de vazios e regenerações que criam nova versão.

## 55-D. Decisões da v1.1

* A regeneração cria sempre nova versão.
* A versão anterior permanece intacta.
* A nova versão é `DRAFT` e `source=SYSTEM`.
* A nova versão copia apenas atribuições manuais/importadas visíveis.
* A nova versão não copia atribuições automáticas antigas.
* Células limpas não regressam como atribuições ativas.
* A regeneração não cria PT, FF, FC, Ronda, CR ou remunerados.

---

## 56-D. Estado implementado na v1.3

A v1.3 acrescentou campos opcionais à tabela `assignments`:

```text
start_time
end_time
duration_minutes
```

Decisões:

* os campos são opcionais para preservar atribuições antigas e códigos sem horário formalizado;
* PT automático preenche sempre os três campos;
* PT manual pode existir sem estes campos, mas o diagnóstico gera aviso;
* `duration_minutes` aceita operacionalmente 360 ou 480 minutos para PT;
* `assignment_selection_details.service_code` passou a aceitar `PT`;
* PT continua a ser uma atribuição principal e não conta para cobertura obrigatória AT/PO.

Migração:

```text
adaa03cbb54b_add_pt_assignment_timing_fields.py
```

---

## 57-D. Estado implementado na v1.4

A v1.4 acrescentou a gestão funcional inicial de FF por trabalho em feriado.

Tabelas criadas:

```text
holidays
holiday_leave_credits
holiday_leave_credit_events
```

Campo acrescentado a `assignments`:

```text
holiday_leave_credit_id
```

Decisões:

* `holidays` não recebe dados iniciais nem feriados fictícios;
* `holiday_leave_credits.source_assignment_id` é único para impedir duplicação da mesma FF;
* a origem da FF preserva militar, feriado, atribuição, versão de origem e código de serviço;
* serviços elegíveis nesta fase: `AT1`, `AT2`, `AT3`, `PO1`, `PO2`, `PO3` e `PT`;
* o dia do feriado mantém o código real executado;
* a célula `FF` agendada fica ligada ao crédito através de `assignments.holiday_leave_credit_id`;
* os eventos de FF registam criação, agendamento, reagendamento, cancelamento de agendamento, gozo e cancelamento do direito;
* `FC`, Ronda, CR, remunerados e exportações continuam fora do âmbito.

Migração:

```text
621f28c3f5b5_add_holiday_leave_credits_v1_4.py
```

---

# PARTE XXII — DECISÕES PENDENTES

## 49. Regras ainda por formalizar

O modelo está preparado para regras ainda não totalmente definidas.

Devem ser formalizadas antes da automatização:

* aquisição e utilização de FC;
* regras completas da Ronda;
* compensações da Ronda;
* regras completas de CR;
* regras completas do Serviço de Pronto;
* serviços que podem coexistir;
* horários finais de AT, PO e outros códigos;
* utilização automática de SEC e SI;
* critérios finais de equilíbrio entre equipas;
* relação entre remunerados e escala normal;
* confirmação de serviços executados;
* tratamento de trocas entre militares.

Enquanto estas regras não forem formalizadas:

* os dados podem ser registados manualmente;
* o sistema pode apresentar avisos;
* não deve inventar automatismos.

---

## 50. Regra final

O modelo de dados deve preservar:

* identidade dos militares;
* histórico das equipas;
* referências do ciclo;
* versões da escala;
* alterações manuais;
* origem das FF;
* serviços remunerados;
* diagnósticos;
* auditoria;
* decisões do Comandante.

Nenhuma simplificação técnica pode justificar:

* apagar histórico;
* eliminar alterações manuais;
* substituir referências do ciclo;
* criar dados fictícios;
* perder a origem de uma decisão;
* ocultar violações autorizadas.

A base de dados deve permitir saber, em qualquer momento:

1. quem estava no efetivo;
2. a que equipa pertencia;
3. qual a referência do ciclo aplicável;
4. que escala estava em vigor;
5. que alterações foram efetuadas;
6. quem efetuou cada alteração;
7. que conflitos existiam;
8. quais foram autorizados;
9. que FF estavam pendentes;
10. como foi escolhido cada militar, sempre que essa explicação esteja disponível.

---

## Nota de Implementacao v1.6 - FC e FR

A v1.6 implementa a infraestrutura funcional de compensacoes com as seguintes tabelas reais:

* `compensatory_leave_credits`;
* `compensatory_leave_credit_events`;
* `rescheduled_rest_credits`;
* `rescheduled_rest_credit_events`.

Foram adicionadas a `assignments` as chaves opcionais:

* `compensatory_leave_credit_id`;
* `rescheduled_rest_credit_id`.

Regras de integridade implementadas:

* uma atribuicao so pode estar ligada a uma das familias `FF`, `FC` ou `FR`;
* codigo `FF` exige `holiday_leave_credit_id`;
* codigo `FC` exige `compensatory_leave_credit_id`;
* codigo `FR` exige `rescheduled_rest_credit_id`;
* outros codigos nao devem possuir ligacoes `FF`/`FC`/`FR`;
* cada FC tem `minutes = 480`;
* cada FC tem `unit_number >= 1` e `units_from_source >= 1`;
* fontes FC controladas: `RONDA`, `CONDUTOR_RONDANTE`, `COMMANDER_DISCRETION`;
* estados FC controlados: `PENDING`, `SCHEDULED`, `RESCHEDULED`, `USED`, `CANCELLED`, `EXPIRED`;
* estados FR controlados: `PENDING`, `SCHEDULED`, `RESCHEDULED`, `USED`, `CANCELLED`;
* origem FR limitada a `AT1`, `AT2`, `AT3`, `PO1`, `PO2`, `PO3` e `PT`;
* tipo de descanso original FR limitado a `DS` ou `DC`.

A migracao aplicada foi `9a4e2b7c1d60_add_fc_fr_compensations_v1_6.py`.

---

## Nota de Implementacao v1.9 - Testes Operacionais

A v1.9 adiciona apenas estrutura necessaria para testes operacionais e avaliacao local.

Campos adicionados a `schedule_versions`:

* `is_operational_test`;
* `test_notes`;
* `test_created_at`;
* `is_archived`;
* `archived_at`;
* `archive_reason`.

Tabelas adicionadas:

* `operational_test_evaluations`;
* `operational_test_evaluation_events`.

Regras de dados:

* `is_operational_test` distingue versoes de afericao local de versoes publicaveis;
* `is_archived` arquiva testes sem usar o estado `CLOSED`;
* decisoes de avaliacao permitidas: `REJECTED`, `ACCEPTABLE_WITH_CHANGES`, `APPROVED_REFERENCE`;
* a importacao operacional reutiliza `militaries` e `military_team_history`;
* o campo CSV `apto_cr` e aceite em pre-visualizacao, mas ainda nao tem coluna funcional persistida;
* nao foram criados modelos de Ronda, CR automatico, remunerados, autenticacao ou auditoria funcional generica.

A migracao aplicada foi `a78b8ff4bc33_add_operational_testing_support_v1_9.py`.
