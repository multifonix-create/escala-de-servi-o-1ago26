# Casos de Teste — Escala de Serviço

**Projeto:** Escala de Serviço  
**Documento:** `TEST_CASES.md`  
**Versão:** 1.0  
**Estado:** Normativo  
**Referência principal:** `docs/ESCALA_RULES.md`

---

## 1. Finalidade do Documento

Este ficheiro define os critérios de validação funcional, técnica e de regressão da aplicação Escala de Serviço.

O objetivo é transformar as regras operacionais em cenários objetivos, verificáveis e reutilizáveis durante o desenvolvimento. Cada caso de teste deve permitir concluir claramente se o resultado é:

* aprovado;
* reprovado;
* bloqueado;
* aprovado com aviso.

Este documento não cria regras operacionais. Quando uma regra ainda não estiver suficientemente formalizada, o caso deve ser marcado como `PENDENTE DE DECISÃO FUNCIONAL`.

---

## 2. Princípios Gerais de Teste

* Todos os testes automáticos devem usar base de dados de testes separada.
* É proibido utilizar `instance/escala.db` nos testes.
* Os testes devem ser determinísticos, isolados, repetíveis e independentes da ordem de execução.
* Os testes não podem apagar, recriar ou modificar a base real.
* Dados existentes, históricos, versões e alterações manuais devem ser preservados.
* Dados pessoais reais não devem ser usados em testes públicos.
* Dados de teste devem usar identificadores neutros: Militar A, Militar B, Equipa A, etc.
* Dados de teste só podem existir em fixtures, diretórios de testes ou base exclusiva de testes.
* Cada bug corrigido deve originar teste de regressão.
* Um teste que dependa de decisão funcional pendente deve ficar bloqueado até essa decisão existir.

---

## 3. Níveis e Tipos de Teste

* **Unitários:** validam uma função, classe ou serviço isolado.
* **Integração:** validam colaboração entre modelos, serviços, repositórios, rotas e base de testes.
* **Funcionais:** validam fluxos completos do ponto de vista do utilizador.
* **Validação:** confirmam regras bloqueantes, avisos e diagnósticos.
* **Regressão:** garantem que erros corrigidos não regressam.
* **Segurança:** validam autenticação, permissões, CSRF e proteção de dados.
* **Desempenho:** medem comportamento com volumes realistas.
* **Exportação:** validam PDF, Excel e formatos futuros.
* **Migrações:** validam evolução da estrutura da base de dados sem perda de dados.
* **Aceitação manual:** validam fluxos revistos pelo responsável funcional.

---

## Formato Comum dos Casos de Teste

Sempre que aplicável, cada caso deve conter:

* Identificador;
* Título;
* Objetivo;
* Regra de origem;
* Tipo de teste;
* Prioridade;
* Pré-condições;
* Dados de entrada;
* Procedimento;
* Resultado esperado;
* Erros ou avisos esperados;
* Dados que devem ser preservados;
* Registos de auditoria esperados;
* Critério de aprovação;
* Observações.

Para evitar repetição, os casos abaixo usam uma forma compacta. Salvo indicação em contrário:

* **Pré-condições:** aplicação em modo de teste, base de testes separada, sem dados pessoais reais.
* **Dados preservados:** base real, histórico existente, versões publicadas, alterações manuais e auditoria.
* **Auditoria esperada:** obrigatória em operações de escrita funcionais; não aplicável a validações puramente unitárias sem persistência.
* **Critério de aprovação:** resultado observado corresponde ao resultado esperado e nenhum dado proibido é criado.

---

## 4. Dados de Teste

Os conjuntos de teste devem ser controlados e existir apenas na base de testes:

* Patrulheiros: Militar A, Militar B, Militar C, etc.
* Equipas: Equipa A, Equipa B, Equipa C, Equipa D e Equipa E.
* SEC: Militar SEC A, Militar SEC B.
* SI: Militar SI A, Militar SI B.
* CMD: Militar CMD A.
* Códigos de serviço: AT1, AT2, AT3, PO1, PO2, PO3, PT, DS, DC, FF, FC, LF, LP, BM, LC, LN, DIL, TRIB, INQ, P, R, CR.
* Feriados: datas neutras configuradas na base de testes.
* Indisponibilidades: completas, parciais e multi-dia.
* Restrições: horárias, semanais, absolutas e exceções positivas.
* Escalas mensais: meses de 28, 29, 30 e 31 dias, incluindo transição anual.

Estes dados não podem ser introduzidos na base real.

---

## 5. Testes do Ciclo de Folgas

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| CYCLE-001 | Seis fases oficiais | ESCALA_RULES 9-18, 197 | Unitário | Crítica | Calcular o ciclo a partir de referência válida; deve produzir Fases 1 a 6 na sequência oficial. |
| CYCLE-002 | Fase 6 passa para Fase 1 | ESCALA_RULES 10, 197 | Regressão | Crítica | Após folga de segunda-feira na Fase 6, próxima folga deve ser sábado/domingo da Fase 1. |
| CYCLE-003 | Continuidade entre semanas | ESCALA_RULES 9-11 | Unitário | Crítica | Calcular blocos consecutivos; a semana civil não deve reiniciar o ciclo. |
| CYCLE-004 | Continuidade entre meses | ESCALA_RULES 11 | Integração | Crítica | Gerar intervalo que atravessa fim de mês; o ciclo deve continuar sem reiniciar. |
| CYCLE-005 | Continuidade entre anos | ESCALA_RULES 11 | Integração | Crítica | Gerar dezembro-janeiro; a viragem anual não deve reiniciar fases. |
| CYCLE-006 | Fevereiro em ano normal | ESCALA_RULES 11 | Unitário | Alta | Calcular fevereiro com 28 dias; todos os blocos devem seguir a sequência contínua. |
| CYCLE-007 | Fevereiro em ano bissexto | ESCALA_RULES 11 | Unitário | Alta | Calcular fevereiro com 29 dias; dia extra não deve deslocar a regra fora da sequência. |
| CYCLE-008 | Mês com 30 dias | ESCALA_RULES 11 | Unitário | Alta | Validar mês de 30 dias; último bloco deve ligar corretamente ao mês seguinte. |
| CYCLE-009 | Mês com 31 dias | ESCALA_RULES 11 | Unitário | Alta | Validar mês de 31 dias; não pode existir reinício artificial. |
| CYCLE-010 | Equipa com referência válida | ESCALA_RULES 12 | Integração | Crítica | Com referência de equipa, cálculo deve devolver blocos, fase e referência usada. |
| CYCLE-011 | Equipa sem referência | ESCALA_RULES 12, 143, 148 | Validação | Crítica | Sem referência, a geração deve bloquear ou emitir erro visível de referência ausente. |
| CYCLE-012 | Referência histórica | ESCALA_RULES 12, 160 | Integração | Alta | Referências antigas devem continuar aplicáveis a datas passadas. |
| CYCLE-013 | Alteração de referência sem alterar passado | ESCALA_RULES 12, 160 | Regressão | Crítica | Criar nova referência futura; escalas anteriores devem permanecer inalteradas. |
| CYCLE-014 | Desfasamento entre equipas | ESCALA_RULES 9-12 | Integração | Alta | Equipas com referências diferentes devem manter ciclos independentes. |
| CYCLE-015 | Blocos de um dia | ESCALA_RULES 16 | Unitário | Crítica | Fases 2 e 6 devem criar apenas um dia de folga. |
| CYCLE-016 | Blocos de dois dias | ESCALA_RULES 17 | Unitário | Crítica | Fases 1, 3, 4 e 5 devem criar dois dias consecutivos. |

---

## 6. Testes DS e DC

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| DSDC-001 | Primeiro dia como DS | ESCALA_RULES 13-17 | Unitário | Crítica | Primeiro dia de qualquer bloco deve receber DS. |
| DSDC-002 | Segundo dia como DC | ESCALA_RULES 17 | Unitário | Crítica | Segundo dia de bloco de dois dias deve receber DC. |
| DSDC-003 | Fase de um dia recebe apenas DS | ESCALA_RULES 16 | Unitário | Crítica | Fases de um dia nunca devem gerar DC. |
| DSDC-004 | Proibição de DC isolado | ESCALA_RULES 16-17, 148 | Validação | Crítica | Uma célula DC sem DS imediatamente anterior deve gerar erro de diagnóstico. |
| DSDC-005 | Proibição de inversão DS/DC | ESCALA_RULES 17 | Validação | Crítica | DC antes de DS no mesmo bloco deve ser erro. |
| DSDC-006 | Trabalho manual sobre DS | ESCALA_RULES 18, 181 | Funcional | Alta | Comandante pode alterar DS manualmente; deve existir aviso, motivo e auditoria. |
| DSDC-007 | Trabalho manual sobre DC | ESCALA_RULES 18, 181 | Funcional | Alta | Comandante pode alterar DC manualmente; deve existir aviso, motivo e auditoria. |
| DSDC-008 | Preservação do ciclo após alteração manual | ESCALA_RULES 18, 203 | Regressão | Crítica | Alterar DS/DC manualmente não pode recalcular nem deslocar o ciclo oficial. |
| DSDC-009 | Crédito compensatório separado | ESCALA_RULES 77-84, 212 | Validação | Alta | Trabalho em folga pode exigir compensação separada; regras incompletas devem ficar `PENDENTE DE DECISÃO FUNCIONAL`. |

---

## 7. Testes de Militares e Equipas

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| MIL-001 | Criar militar sem dados fictícios automáticos | ESCALA_RULES 164 | Funcional | Crítica | Criar Militar A; sistema não deve criar outros militares, equipas ou escalas. |
| MIL-002 | Militar ativo | ESCALA_RULES 46 | Validação | Crítica | Militar ativo dentro das datas deve ser elegível se cumprir restantes regras. |
| MIL-003 | Militar inativo | ESCALA_RULES 46, 162 | Validação | Crítica | Militar inativo não deve ser considerado em gerações futuras. |
| MIL-004 | Data de início | ESCALA_RULES 47 | Validação | Alta | Antes da data de início, militar não pode ser escalado. |
| MIL-005 | Data de fim | ESCALA_RULES 47 | Validação | Alta | Após data de fim, militar não pode ser escalado. |
| MIL-006 | Patrulheiro pertence a equipa | ESCALA_RULES 5 | Validação | Crítica | Patrulheiro ativo deve ter equipa operacional válida. |
| MIL-007 | Mudança de equipa | ESCALA_RULES 160 | Funcional | Alta | Alterar equipa com data de efeito; nova data usa nova equipa. |
| MIL-008 | Preservação do histórico de equipa | ESCALA_RULES 5, 159-160 | Regressão | Crítica | Mudança de equipa não altera escalas anteriores. |
| MIL-009 | Militar sem equipa | ESCALA_RULES 5 | Validação | Alta | Patrulheiro ativo sem equipa deve bloquear geração operacional. |
| MIL-010 | Militar em duas equipas simultâneas | ESCALA_RULES 5, DATA_MODEL 7 | Validação | Crítica | Sobreposição de pertenças deve ser rejeitada ou diagnosticada como erro. |
| MIL-011 | SEC | ESCALA_RULES 6 | Funcional | Alta | SEC tem horário normal e pode ser chamado para AT/PO quando necessário. |
| MIL-012 | SI | ESCALA_RULES 7 | Funcional | Alta | SI segue regras de SEC. |
| MIL-013 | CMD | ESCALA_RULES 8 | Validação | Crítica | CMD não pode executar AT, PO ou PT. |
| MIL-014 | Eliminar versus desativar | ESCALA_RULES 161-163 | Segurança | Crítica | Eliminação definitiva deve ser excecional; desativação é fluxo normal. |
| MIL-015 | Eliminar militar com histórico | ESCALA_RULES 163 | Validação | Crítica | Tentativa deve ser bloqueada, preservando histórico e auditoria. |
| MIL-016 | Nome e sobrenome obrigatórios | Melhoria pós-v1.9 | Validação | Alta | Criação/edição exige `nome` e `sobrenome`, gerando `full_name` central. |
| MIL-017 | Contacto português obrigatório | Melhoria pós-v1.9 | Validação | Alta | Contacto aceita `912345678` ou `+351912345678`, normaliza como texto e rejeita formato inválido. |
| MIL-018 | Voluntário remunerados informativo | Melhoria pós-v1.9 | Funcional | Média | Checkbox fica persistida, mas não altera geração, FF, FC, diagnósticos ou exportações. |
| MIL-019 | Acesso direto a restrições | Melhoria pós-v1.9 | Interface | Alta | Criar/editar/detalhe/lista permitem chegar às restrições do militar sem duplicar sistema de restrições. |
| MIL-020 | Compatibilidade de nome legado | Melhoria pós-v1.9 | Regressão | Alta | Registos antigos com apenas `name` continuam a apresentar nome completo por `full_name`. |

---

## 8. Testes de Cobertura Mínima

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| COVERAGE-001 | AT1 com 1 militar | ESCALA_RULES 21, 23 | Validação | Crítica | Um militar em AT1 satisfaz mínimo do turno. |
| COVERAGE-002 | AT2 com 1 militar | ESCALA_RULES 21, 23 | Validação | Crítica | Um militar em AT2 satisfaz mínimo do turno. |
| COVERAGE-003 | AT3 com 1 militar | ESCALA_RULES 21, 23 | Validação | Crítica | Um militar em AT3 satisfaz mínimo do turno. |
| COVERAGE-004 | PO1 com 2 militares | ESCALA_RULES 22, 23 | Validação | Crítica | Dois militares em PO1 satisfazem mínimo do turno. |
| COVERAGE-005 | PO2 com 2 militares | ESCALA_RULES 22, 23 | Validação | Crítica | Dois militares em PO2 satisfazem mínimo do turno. |
| COVERAGE-006 | PO3 com 2 militares | ESCALA_RULES 22, 23 | Validação | Crítica | Dois militares em PO3 satisfazem mínimo do turno. |
| COVERAGE-007 | Cobertura total de 9 | ESCALA_RULES 23 | Validação | Crítica | AT1+AT2+AT3+PO1+PO2+PO3 devem totalizar 9 mínimos diários. |
| COVERAGE-008 | Falta de 1 militar | ESCALA_RULES 24, 146 | Validação | Crítica | Deve emitir erro com turno, falta e candidatos excluídos. |
| COVERAGE-009 | Falta em vários turnos | ESCALA_RULES 24, 146 | Validação | Crítica | Deve listar cada turno em falta separadamente. |
| COVERAGE-010 | Cobertura excedente | ESCALA_RULES 23-24 | Funcional | Média | Excedente não é erro se não violar incompatibilidades ou descanso. |
| COVERAGE-011 | Ausência de PT sem erro crítico | ESCALA_RULES 26-29, 145 | Validação | Alta | Falta de PT deve ser informação, não erro bloqueante. |
| COVERAGE-012 | Uso de SEC ou SI por necessidade | ESCALA_RULES 6-7, 144 | Funcional | Alta | Recurso a SEC/SI deve ser justificado e registado como aviso quando aplicável. |
| COVERAGE-013 | Impossibilidade total de cobertura | ESCALA_RULES 24 | Validação | Crítica | Sistema não inventa militares; deve bloquear validação/publicação. |
| COVERAGE-014 | Explicação dos candidatos excluídos | ESCALA_RULES 24, 51 | Integração | Crítica | Diagnóstico deve explicar exclusões por indisponibilidade, folga, descanso, restrição ou inatividade. |

---

## 9. Testes do Descanso Mínimo

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| REST-001 | Exatamente 8 horas | ESCALA_RULES 19, 147 | Unitário | Crítica | Descanso de 8h deve ser aprovado. |
| REST-002 | 7 horas e 59 minutos | ESCALA_RULES 19 | Unitário | Crítica | Deve gerar aviso/violação de descanso. |
| REST-003 | Mais de 8 horas | ESCALA_RULES 19 | Unitário | Alta | Deve ser aprovado. |
| REST-004 | Mudança de dia | ESCALA_RULES 19, 147 | Unitário | Crítica | Cálculo deve usar data e hora reais. |
| REST-005 | Mudança de mês | ESCALA_RULES 19, 147 | Unitário | Alta | Descanso entre último dia do mês e primeiro do mês seguinte deve ser calculado corretamente. |
| REST-006 | Mudança de ano | ESCALA_RULES 19, 147 | Unitário | Alta | Descanso entre 31 de dezembro e 1 de janeiro deve ser calculado corretamente. |
| REST-007 | AT1 após serviço anterior | ESCALA_RULES 19, 21 | Integração | Crítica | AT1 deve ser recusado ou avisado se descanso anterior for inferior a 8h. |
| REST-008 | PO1 após serviço anterior | ESCALA_RULES 19, 22 | Integração | Crítica | PO1 deve respeitar descanso mínimo. |
| REST-009 | Serviço noturno seguido de diurno | ESCALA_RULES 19 | Integração | Crítica | Deve considerar fim real do serviço noturno e início real do diurno. |
| REST-010 | Indisponibilidade entre serviços | ESCALA_RULES 40-41 | Integração | Alta | Mesmo sem serviço, indisponibilidade pode afetar descanso e gerar aviso. |
| REST-011 | Override autorizado | ESCALA_RULES 19, 144 | Funcional | Alta | Override com motivo e permissões deve aprovar com aviso e auditoria. |
| REST-012 | Override sem motivo | ESCALA_RULES 19, 157 | Validação | Crítica | Deve ser bloqueado ou exigir motivo. |
| REST-013 | Auditoria do override | ESCALA_RULES 19, 155-158 | Auditoria | Crítica | Deve registar utilizador, motivo, data e serviços envolvidos. |

---

## 10. Testes das Restrições Individuais

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| RESTR-001 | Restrição diária | ESCALA_RULES 42 | Validação | Alta | Militar restrito num dia não deve receber serviço incompatível. |
| RESTR-002 | Restrição por intervalo horário | ESCALA_RULES 40-42 | Validação | Crítica | Deve comparar sobreposição real de horas. |
| RESTR-003 | Restrição por dias da semana | ESCALA_RULES 42-43 | Validação | Alta | Restrição semanal só se aplica aos dias configurados. |
| RESTR-004 | Restrição com data de início | ESCALA_RULES 42 | Validação | Alta | Antes da data inicial, restrição não se aplica. |
| RESTR-005 | Restrição com data de fim | ESCALA_RULES 42 | Validação | Alta | Após a data final, restrição não se aplica. |
| RESTR-006 | Restrição sem data de fim | ESCALA_RULES 42 | Validação | Alta | Restrição deve manter-se ativa até ser encerrada. |
| RESTR-007 | Indisponibilidade das 08:00 às 14:00 | ESCALA_RULES 42 | Integração | Crítica | Serviços sobrepostos a esse intervalo devem ser recusados ou avisados. |
| RESTR-008 | Disponibilidade especial noturna | ESCALA_RULES 43-44 | Validação | Alta | Disponibilidade especial só autoriza o turno definido. |
| RESTR-009 | Exceção positiva | ESCALA_RULES 43 | Funcional | Alta | Exceção não elimina restrição geral. |
| RESTR-010 | Conflito entre restrição absoluta e exceção | ESCALA_RULES 44 | Validação | Crítica | Restrição absoluta prevalece. |
| RESTR-011 | Prioridade da restrição absoluta | ESCALA_RULES 25, 44 | Validação | Crítica | Geração automática não pode ultrapassar restrição absoluta. |

---

## 11. Testes das Indisponibilidades

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| UNAV-001 | LF | ESCALA_RULES 32-33 | Validação | Crítica | LF bloqueia AT, PO e PT incompatíveis. |
| UNAV-002 | LP | ESCALA_RULES 32, 34 | Validação | Alta | LP deve usar legenda/configuração oficial e bloquear incompatíveis. |
| UNAV-003 | BM | ESCALA_RULES 32, 35 | Validação | Crítica | BM impede serviço operacional. |
| UNAV-004 | LC | ESCALA_RULES 32, 36 | Validação | Alta | LC impede serviços incompatíveis. |
| UNAV-005 | LN | ESCALA_RULES 32, 36 | Validação | Alta | LN impede serviços incompatíveis. |
| UNAV-006 | DIL | ESCALA_RULES 37 | Integração | Alta | Diligência deve considerar início, fim, deslocação e descanso. |
| UNAV-007 | TRIB | ESCALA_RULES 38 | Integração | Alta | Tribunal deve bloquear período necessário. |
| UNAV-008 | INQ | ESCALA_RULES 39 | Integração | Alta | Inquérito segue regras temporais das diligências. |
| UNAV-009 | Dia completo | ESCALA_RULES 40 | Validação | Alta | Indisponibilidade de dia completo bloqueia todo o dia. |
| UNAV-010 | Intervalo parcial | ESCALA_RULES 40-41 | Validação | Alta | Bloqueia apenas serviços sobrepostos ou descanso afetado. |
| UNAV-011 | Vários dias | ESCALA_RULES 40 | Validação | Alta | Bloqueia todos os dias abrangidos. |
| UNAV-012 | Sobreposição total | ESCALA_RULES 41 | Validação | Crítica | Serviço totalmente sobreposto deve ser recusado. |
| UNAV-013 | Sobreposição parcial | ESCALA_RULES 41 | Validação | Crítica | Serviço parcialmente sobreposto deve gerar conflito. |
| UNAV-014 | Ausência de sobreposição | ESCALA_RULES 41 | Validação | Média | Sem sobreposição e com descanso suficiente, deve aprovar. |
| UNAV-015 | Descanso afetado sem sobreposição | ESCALA_RULES 41 | Validação | Alta | Deve gerar aviso de descanso. |
| UNAV-016 | Edição de indisponibilidade | ESCALA_RULES 155-157 | Funcional | Alta | Deve preservar valor anterior e auditar alteração. |
| UNAV-017 | Eliminação de indisponibilidade | ESCALA_RULES 158, 166 | Funcional | Alta | Deve exigir confirmação e preservar histórico quando aplicável. |
| UNAV-018 | Compensação quando recai em folga | ESCALA_RULES 212 | Validação | Média | Marcar `PENDENTE DE DECISÃO FUNCIONAL` se a regra de compensação não estiver definida. |

---

## 12. Testes do PT

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| PT-001 | PT só depois de AT e PO | ESCALA_RULES 26-29 | Integração | Crítica | PT apenas pode ser atribuído após mínimos obrigatórios preenchidos. |
| PT-002 | PT com efetivo sobrante | ESCALA_RULES 26, 28 | Funcional | Alta | Com sobrantes válidos, PT pode ser atribuído. |
| PT-003 | Ausência de sobrantes | ESCALA_RULES 28-29 | Validação | Alta | Sem sobrantes, não deve ser criado PT. |
| PT-004 | PT de 6 horas | ESCALA_RULES 27 | Validação | Média | Duração de 6h deve ficar registada. |
| PT-005 | PT de 8 horas | ESCALA_RULES 27 | Validação | Média | Duração de 8h deve ficar registada. |
| PT-006 | PT em DS | ESCALA_RULES 18, 26, 28 | Validação | Crítica | PT em DS automático é proibido; manual exige aviso e auditoria. |
| PT-007 | PT em DC | ESCALA_RULES 18, 26, 28 | Validação | Crítica | PT em DC automático é proibido; manual exige aviso e auditoria. |
| PT-008 | PT durante indisponibilidade | ESCALA_RULES 26, 32 | Validação | Crítica | Deve ser bloqueado salvo override autorizado quando permitido. |
| PT-009 | PT com descanso insuficiente | ESCALA_RULES 19, 28 | Validação | Crítica | Deve gerar aviso/bloqueio de descanso. |
| PT-010 | PT não contado como falha de cobertura | ESCALA_RULES 29 | Validação | Alta | Ausência de PT é informação, não erro crítico. |
| PT-011 | Prioridade reduzida do PT | ESCALA_RULES 26, 29 | Integração | Alta | PT nunca prevalece sobre AT, PO, descanso, DS/DC, indisponibilidades ou restrições. |

---

## 13. Testes SEC e SI

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| SECSI-001 | Horário normal segunda a sexta | ESCALA_RULES 6-7 | Funcional | Média | SEC/SI trabalham 09:00-17:00 em dias úteis, salvo serviço atribuído. |
| SECSI-002 | Folga sábado e domingo | ESCALA_RULES 6-7 | Funcional | Média | SEC/SI folgam ao fim de semana no regime normal. |
| SECSI-003 | Chamada para AT | ESCALA_RULES 6-7, 25 | Funcional | Alta | Podem ser usados em AT quando necessário e justificado. |
| SECSI-004 | Chamada para PO | ESCALA_RULES 6-7, 25 | Funcional | Alta | Podem ser usados em PO quando necessário e justificado. |
| SECSI-005 | Substituição do serviço normal | ESCALA_RULES 6-7 | Validação | Alta | AT/PO substitui horário normal; não deve duplicar código principal. |
| SECSI-006 | Proibição de duplicação de códigos | ESCALA_RULES 30 | Validação | Crítica | Não pode existir serviço normal e AT/PO principal no mesmo dia. |
| SECSI-007 | Utilização apenas por necessidade | ESCALA_RULES 25, 52 | Integração | Alta | Seleção deve explicar necessidade antes de recorrer a SEC/SI. |
| SECSI-008 | Descanso | ESCALA_RULES 19 | Validação | Crítica | SEC/SI também cumprem descanso mínimo. |
| SECSI-009 | Restrições e justificação | ESCALA_RULES 42-45, 51 | Integração | Alta | Restrições devem ser respeitadas e a seleção deve ficar explicada. |

---

## 14. Testes CMD, P, R e CR

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| CMD-001 | CMD excluído de AT | ESCALA_RULES 8 | Validação | Crítica | Comandante não pode ser selecionado automaticamente para AT. |
| CMD-002 | CMD excluído de PO | ESCALA_RULES 8 | Validação | Crítica | Comandante não pode ser selecionado automaticamente para PO. |
| CMD-003 | CMD excluído de PT | ESCALA_RULES 8 | Validação | Crítica | Comandante não pode ser selecionado automaticamente para PT. |
| CMD-004 | Código P | ESCALA_RULES 8, 212 | Validação | Média | Regras completas de P devem ser marcadas `PENDENTE DE DECISÃO FUNCIONAL`. |
| CMD-005 | Ronda de 24 horas | ESCALA_RULES 212 | Validação | Alta | Regras completas de R devem ficar pendentes se não formalizadas. |
| CMD-006 | Aptidão para ronda | ESCALA_RULES 45 | Validação | Alta | Apenas militares aptos podem ser candidatos; detalhes pendentes se regra incompleta. |
| CMD-007 | Ronda em dia útil | ESCALA_RULES 212 | Validação | Média | Marcar `PENDENTE DE DECISÃO FUNCIONAL` quanto a efeitos e compensações. |
| CMD-008 | Ronda iniciada à sexta-feira | ESCALA_RULES 212 | Regressão | Alta | Marcar `PENDENTE DE DECISÃO FUNCIONAL` até regra final. |
| CMD-009 | Ronda ao sábado | ESCALA_RULES 212 | Regressão | Alta | Marcar `PENDENTE DE DECISÃO FUNCIONAL` até regra final. |
| CMD-010 | Criação de compensação | ESCALA_RULES 77-84, 212 | Validação | Alta | FC/compensação por ronda deve aguardar decisão funcional. |
| CMD-011 | Associação entre ronda e CR | ESCALA_RULES 212 | Integração | Alta | Origem do CR deve ser rastreável; regra operacional pendente se incompleta. |
| CMD-012 | CR manual | ESCALA_RULES 30, 212 | Funcional | Média | CR manual deve exigir motivo e auditoria. |
| CMD-013 | CR sem origem | ESCALA_RULES 157, 212 | Validação | Alta | Deve gerar alerta ou ficar pendente conforme regra definida. |
| CMD-014 | Alerta | ESCALA_RULES 144 | Diagnóstico | Média | Situações incompletas devem aparecer como aviso. |
| CMD-015 | Override | ESCALA_RULES 19, 155-158 | Auditoria | Alta | Override deve registar motivo, utilizador e data. |

---

## 15. Testes de FF

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| FF-001 | Trabalho num feriado | ESCALA_RULES 85-94, 201 | Integração | Crítica | Serviço executado em feriado deve poder originar FF. |
| FF-002 | Manutenção do código real no feriado | ESCALA_RULES 85-94 | Regressão | Crítica | O dia do feriado mantém AT/PO/R real; FF é crédito separado. |
| FF-003 | Criação do crédito | ESCALA_RULES 85-94 | Integração | Crítica | Crédito FF deve guardar militar, feriado e origem. |
| FF-004 | FF pendente | ESCALA_RULES 85-94 | Validação | Alta | Crédito criado fica pendente até agendamento. |
| FF-005 | FF pendente não ocupa célula | ESCALA_RULES 85-94 | Validação | Crítica | FF pendente não altera escala mensal. |
| FF-006 | Transição entre meses | ESCALA_RULES 201 | Integração | Alta | FF pendente deve transitar para mês seguinte. |
| FF-007 | Agendamento | ESCALA_RULES 85-94 | Funcional | Alta | Agendar FF cria célula/atribuição correspondente. |
| FF-008 | Cobertura no dia escolhido | ESCALA_RULES 23-24, 85-94 | Validação | Crítica | Agendamento não deve quebrar mínimos sem aviso/decisão. |
| FF-009 | FF agendada | ESCALA_RULES 85-94 | Funcional | Alta | Estado deve passar para agendada e preservar origem. |
| FF-010 | FF gozada | ESCALA_RULES 85-94 | Funcional | Alta | Após confirmação, estado deve passar para gozada. |
| FF-011 | Confirmação posterior ao dia | ESCALA_RULES 210 | Funcional | Média | Confirmação deve consolidar histórico após execução. |
| FF-012 | Reagendamento | ESCALA_RULES 85-94 | Funcional | Alta | Reagendar preserva origem e regista evento. |
| FF-013 | Cancelamento do agendamento | ESCALA_RULES 85-94 | Funcional | Alta | Cancelar agendamento deve voltar a pendente quando aplicável. |
| FF-014 | Regresso a pendente | ESCALA_RULES 85-94 | Validação | Alta | Estado e célula devem ficar coerentes. |
| FF-015 | Cancelamento do direito | ESCALA_RULES 85-94 | Funcional | Alta | Exige motivo e auditoria. |
| FF-016 | Motivo obrigatório | ESCALA_RULES 155-157 | Validação | Alta | Cancelamentos relevantes sem motivo devem ser bloqueados. |
| FF-017 | Saldo | ESCALA_RULES 201 | Integração | Alta | Saldo deve refletir pendentes, agendadas e gozadas. |
| FF-018 | Histórico e auditoria | ESCALA_RULES 155-159, 201 | Auditoria | Crítica | Todos os eventos de FF devem ficar registados. |
| FF-019 | Alteração posterior da tabela de feriados | ESCALA_RULES 85-94, DATA_MODEL 29 | Regressão | Alta | FF adquirida não deve ser apagada por alteração posterior do feriado. |
| FF-020 | Preservação do direito adquirido | ESCALA_RULES 85-94 | Regressão | Crítica | Direito mantém origem e estado histórico. |

---

## 16. Testes de FC

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| FC-001 | Criação com origem | ESCALA_RULES 77-84, 202, 212 | Validação | Alta | Deve exigir origem identificável; detalhes pendentes se regra incompleta. |
| FC-002 | Criação sem origem | ESCALA_RULES 77-84, 202 | Validação | Crítica | Deve bloquear ou marcar `PENDENTE DE DECISÃO FUNCIONAL`. |
| FC-003 | Ronda | ESCALA_RULES 202, 212 | Validação | Alta | FC associada a ronda está `PENDENTE DE DECISÃO FUNCIONAL`. |
| FC-004 | Trabalho em folga | ESCALA_RULES 202, 212 | Validação | Alta | FC por trabalho em DS/DC está `PENDENTE DE DECISÃO FUNCIONAL`. |
| FC-005 | Estado pendente | ESCALA_RULES 202 | Funcional | Média | Crédito, quando válido, deve poder ficar pendente. |
| FC-006 | Agendada | ESCALA_RULES 202 | Funcional | Média | Agendamento deve preservar origem. |
| FC-007 | Gozada | ESCALA_RULES 202 | Funcional | Média | Gozo deve atualizar estado e histórico. |
| FC-008 | Reagendada | ESCALA_RULES 202 | Funcional | Média | Reagendamento deve criar evento. |
| FC-009 | Cancelamento de agendamento | ESCALA_RULES 202 | Funcional | Média | Cancelamento deve preservar direito quando aplicável. |
| FC-010 | Saldo | ESCALA_RULES 202 | Integração | Média | Saldo deve refletir estados válidos. |
| FC-011 | Associação ao serviço | ESCALA_RULES 202 | Integração | Alta | Crédito deve ligar ao serviço de origem quando a regra existir. |
| FC-012 | Histórico | ESCALA_RULES 159 | Auditoria | Alta | Histórico deve preservar eventos. |
| FC-013 | Auditoria | ESCALA_RULES 155-157 | Auditoria | Alta | Criação, agendamento e cancelamento devem ser auditados. |

---

## 17. Testes de Serviços Remunerados

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| REM-001 | Preferência | ESCALA_RULES 95-103 | Funcional | Alta | Preferências devem influenciar seleção conforme regra definida. |
| REM-002 | Indisponibilidade | ESCALA_RULES 32, 95-103 | Validação | Crítica | Indisponível não deve ser selecionado. |
| REM-003 | Descanso | ESCALA_RULES 19, 95-103 | Validação | Crítica | Remunerado deve respeitar descanso ou override autorizado. |
| REM-004 | Conflito com escala normal | ESCALA_RULES 30-31, 95-103 | Validação | Crítica | Serviço incompatível deve ser bloqueado/avisado. |
| REM-005 | Aptidão | ESCALA_RULES 45 | Validação | Alta | Militar sem aptidão não deve ser elegível. |
| REM-006 | Equidade | ESCALA_RULES 52-57, 95-103 | Integração | Alta | Seleção deve considerar totais e histórico. |
| REM-007 | Candidatos excluídos | ESCALA_RULES 51 | Diagnóstico | Alta | Deve explicar exclusões. |
| REM-008 | Explicação da seleção | ESCALA_RULES 52, 95-103 | Integração | Alta | Critérios usados devem ficar registados. |
| REM-009 | Registo de horas | DATA_MODEL 31 | Integração | Média | Deve guardar início, fim e data. |
| REM-010 | Separação financeira | ESCALA_RULES 95-103 | Validação | Média | Lógica financeira não deve alterar regras da escala normal. |

---

## 18. Testes de Serviços Especiais

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| SPECIAL-001 | Criação | DATA_MODEL 33 | Funcional | Média | Criar serviço especial na base de testes com estado e autoria. |
| SPECIAL-002 | Local | ESCALA_RULES 153-154 | Funcional | Baixa | Local deve ser registável quando aplicável. |
| SPECIAL-003 | Horário | DATA_MODEL 33 | Validação | Alta | Início e fim devem ser coerentes. |
| SPECIAL-004 | Número de militares | ESCALA_RULES 24, DATA_MODEL 34 | Validação | Média | Número exigido deve ser configurado, não inventado. |
| SPECIAL-005 | Participantes | DATA_MODEL 34 | Integração | Média | Participantes devem ficar ligados ao serviço. |
| SPECIAL-006 | Aptidões | ESCALA_RULES 45 | Validação | Alta | Aptidões exigidas devem ser respeitadas. |
| SPECIAL-007 | Conflito | ESCALA_RULES 30-31 | Validação | Alta | Conflito com código principal deve gerar erro/aviso. |
| SPECIAL-008 | Substituição do serviço normal | ESCALA_RULES 30-31 | Funcional | Média | Substituição deve ser explícita e auditada. |
| SPECIAL-009 | Atividade adicional compatível | ESCALA_RULES 31 | Validação | Média | Pode coexistir se compatibilidade estiver configurada. |
| SPECIAL-010 | Atividade adicional incompatível | ESCALA_RULES 31 | Validação | Alta | Não pode esconder incompatibilidades. |
| SPECIAL-011 | Auditoria | ESCALA_RULES 155-157 | Auditoria | Alta | Criação/alteração deve ser auditada. |

---

## 19. Testes de Geração

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| GEN-001 | Pré-validação | ESCALA_RULES 24-25, 214 | Integração | Crítica | Antes de gerar, validar dados necessários. |
| GEN-002 | Ausência de militares | ESCALA_RULES 24, 164 | Validação | Crítica | Deve bloquear e não criar militares fictícios. |
| GEN-003 | Equipa sem referência | ESCALA_RULES 12, 148 | Validação | Crítica | Deve bloquear geração ou emitir erro. |
| GEN-004 | Código inexistente | ESCALA_RULES 172-174 | Validação | Crítica | Deve bloquear ou avisar conforme criticidade. |
| GEN-005 | Cobertura inexistente | ESCALA_RULES 23-24 | Validação | Crítica | Deve diagnosticar ausência de cobertura configurada. |
| GEN-006 | Geração inicial | ESCALA_RULES 20-25 | Integração | Crítica | Deve criar rascunho e versão sem dados fictícios. |
| GEN-007 | Aplicação de DS/DC | ESCALA_RULES 13-18 | Integração | Crítica | Folgas do ciclo devem ser aplicadas antes dos serviços normais. |
| GEN-008 | Aplicação de indisponibilidades | ESCALA_RULES 32-41 | Integração | Crítica | Indisponibilidades ativas devem bloquear serviços incompatíveis. |
| GEN-009 | Preenchimento de obrigatórios | ESCALA_RULES 20-25 | Integração | Crítica | AT e PO devem ser preenchidos até mínimos quando possível. |
| GEN-010 | PT apenas no final | ESCALA_RULES 26-29 | Integração | Alta | PT atribuído só depois dos obrigatórios. |
| GEN-011 | Criação da versão | ESCALA_RULES 209-210 | Integração | Alta | Nova geração deve criar versão identificada. |
| GEN-012 | Registo da execução | ESCALA_RULES 155-157 | Auditoria | Alta | Execução deve ficar registada. |
| GEN-013 | Erros | ESCALA_RULES 143 | Diagnóstico | Crítica | Erros bloqueantes devem impedir validação. |
| GEN-014 | Avisos | ESCALA_RULES 144 | Diagnóstico | Alta | Avisos devem ser visíveis e autorizáveis quando permitido. |
| GEN-015 | Determinismo | ESCALA_RULES 3.2, 52 | Regressão | Crítica | Mesma entrada deve produzir mesmo resultado. |
| GEN-016 | Repetição determinística | ESCALA_RULES 3.2, 203 | Regressão | Crítica | Reexecutar geração em base de testes equivalente deve manter resultado. |

---

## 20. Testes de Seleção e Equidade

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| EQUITY-001 | Menor carga | ESCALA_RULES 52-57 | Unitário | Alta | Ordenação deve privilegiar menor carga do serviço. |
| EQUITY-002 | Menor número de noites | ESCALA_RULES 52-57 | Unitário | Alta | Em empate anterior, menor carga noturna prevalece. |
| EQUITY-003 | Menor número de fins de semana | ESCALA_RULES 52-57 | Unitário | Alta | Fins de semana devem contar para equidade. |
| EQUITY-004 | Serviços consecutivos | ESCALA_RULES 52, 58 | Validação | Média | Sequências excessivas devem gerar alerta configurável. |
| EQUITY-005 | Equilíbrio entre equipas | ESCALA_RULES 52, 55 | Integração | Alta | Seleção deve considerar distribuição por equipa. |
| EQUITY-006 | Última atribuição equivalente | ESCALA_RULES 52 | Unitário | Alta | Maior intervalo desde serviço equivalente deve influenciar. |
| EQUITY-007 | Desempate estável | ESCALA_RULES 52 | Unitário | Crítica | Empate total deve usar identificador estável. |
| EQUITY-008 | Proibição de aleatoriedade | ESCALA_RULES 3.2, 52 | Regressão | Crítica | Não pode existir sorteio não registado. |
| EQUITY-009 | Militar inelegível não penalizado | ESCALA_RULES 54 | Validação | Alta | Inelegível não deve ser comparado como se pudesse executar serviço. |
| EQUITY-010 | Serviço manual conta para equidade | ESCALA_RULES 57 | Integração | Alta | Manual deve contar salvo regra em contrário. |
| EQUITY-011 | Período histórico configurável | ESCALA_RULES 56 | Integração | Média | Período de análise não deve limitar-se ao mês atual. |
| EQUITY-012 | Explicação da escolha | ESCALA_RULES 51-52 | Integração | Alta | Critérios e exclusões devem ser recuperáveis. |

---

## 21. Testes de Edição Manual

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| MANUAL-001 | Alteração válida | ESCALA_RULES 155-158, 181 | Funcional | Alta | Alteração compatível deve guardar valor anterior e novo. |
| MANUAL-002 | Alteração incompatível | ESCALA_RULES 30-31 | Validação | Crítica | Deve apresentar erro ou aviso conforme regra. |
| MANUAL-003 | Aviso | ESCALA_RULES 144 | Funcional | Alta | Aviso deve ser visível antes de confirmar. |
| MANUAL-004 | Erro bloqueante | ESCALA_RULES 143 | Validação | Crítica | Erro bloqueante não deve ser confirmado sem regra de override. |
| MANUAL-005 | Motivo | ESCALA_RULES 157 | Validação | Alta | Motivo deve ser obrigatório quando há override/violação. |
| MANUAL-006 | Proteção | ESCALA_RULES 203 | Regressão | Crítica | Célula manual deve ficar protegida contra regeneração. |
| MANUAL-007 | Indicação visual | ESCALA_RULES 181 | Interface | Média | Alteração manual deve ser distinguível. |
| MANUAL-008 | Override | ESCALA_RULES 19, 155-157 | Funcional | Alta | Override deve registar autorização. |
| MANUAL-009 | Alteração do valor anterior | ESCALA_RULES 157 | Auditoria | Alta | Valor anterior deve ser preservado. |
| MANUAL-010 | Preservação do histórico | ESCALA_RULES 159 | Regressão | Crítica | Alteração não apaga histórico. |
| MANUAL-011 | Utilizador sem permissão | ESCALA_RULES 182-186 | Segurança | Crítica | Deve bloquear operação e registar tentativa se aplicável. |

---

## 22. Testes de Regeneração

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| REGEN-001 | Completar células vazias | ESCALA_RULES 203 | Integração | Alta | Regeneração pode preencher vazios permitidos. |
| REGEN-002 | Regenerar apenas automáticos | ESCALA_RULES 203 | Regressão | Crítica | Apenas células automáticas podem ser substituídas. |
| REGEN-003 | Preservar manuais | ESCALA_RULES 3.4, 203 | Regressão | Crítica | Células manuais permanecem inalteradas. |
| REGEN-004 | Preservar overrides | ESCALA_RULES 203 | Regressão | Crítica | Overrides autorizados permanecem rastreáveis. |
| REGEN-005 | Célula desbloqueada | ESCALA_RULES 203 | Funcional | Alta | Célula desbloqueada pode ser recalculada. |
| REGEN-006 | Nova versão | ESCALA_RULES 209-210 | Integração | Alta | Regeneração deve criar nova versão quando aplicável. |
| REGEN-007 | Ausência de duplicações | ESCALA_RULES 30, DATA_MODEL 18 | Regressão | Crítica | Não pode duplicar célula principal por militar/data/versão. |
| REGEN-008 | Determinismo | ESCALA_RULES 3.2 | Regressão | Crítica | Mesma entrada gera mesmo resultado. |
| REGEN-009 | Após alteração de dados | ESCALA_RULES 203 | Integração | Alta | Deve preservar manuais e recalcular apenas permitido. |
| REGEN-010 | Comparação com versão anterior | ESCALA_RULES 209-210 | Funcional | Média | Diferenças entre versões devem ser auditáveis. |

---

## 23. Testes de Estados da Escala

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| STATE-001 | Não gerada | ESCALA_RULES 209 | Funcional | Alta | Mês sem geração deve aparecer como não gerado. |
| STATE-002 | Rascunho | ESCALA_RULES 209 | Funcional | Alta | Geração inicial cria rascunho. |
| STATE-003 | Validada | ESCALA_RULES 209 | Funcional | Alta | Só pode validar sem erros bloqueantes. |
| STATE-004 | Publicada | ESCALA_RULES 209 | Funcional | Alta | Publicação exige validação e diagnóstico essencial. |
| STATE-005 | Encerrada | ESCALA_RULES 210 | Funcional | Alta | Encerramento exige consolidação e histórico. |
| STATE-006 | Validação com erros | ESCALA_RULES 151 | Validação | Crítica | Erros bloqueantes impedem validação. |
| STATE-007 | Publicação com erros | ESCALA_RULES 152, 209 | Validação | Crítica | Erros bloqueantes impedem publicação. |
| STATE-008 | Publicação com avisos | ESCALA_RULES 144, 209 | Funcional | Alta | Avisos devem ser apresentados e tratados. |
| STATE-009 | Alteração após publicação | ESCALA_RULES 209 | Funcional | Alta | Deve criar nova versão/reabertura conforme regra. |
| STATE-010 | Encerramento | ESCALA_RULES 210 | Funcional | Alta | Deve preservar versão encerrada. |
| STATE-011 | Reabertura | ESCALA_RULES 209 | Funcional | Alta | Deve exigir motivo e criar nova versão. |
| STATE-012 | Motivo | ESCALA_RULES 157, 209 | Validação | Alta | Transições críticas exigem motivo. |
| STATE-013 | Auditoria | ESCALA_RULES 155-157 | Auditoria | Crítica | Todas as transições devem ser auditadas. |

---

## 24. Testes de Diagnóstico

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| DIAG-001 | Erro | ESCALA_RULES 143 | Validação | Crítica | Situação bloqueante deve ser classificada como erro. |
| DIAG-002 | Aviso | ESCALA_RULES 144 | Validação | Alta | Situação autorizável deve ser aviso. |
| DIAG-003 | Informação | ESCALA_RULES 145 | Validação | Média | Situação informativa não deve bloquear. |
| DIAG-004 | Cobertura | ESCALA_RULES 146 | Integração | Crítica | Deve indicar mínimos, atribuídos e faltas. |
| DIAG-005 | Descanso | ESCALA_RULES 147 | Integração | Crítica | Deve indicar serviços, horas e mínimo exigido. |
| DIAG-006 | Ciclo | ESCALA_RULES 148 | Integração | Crítica | Deve validar fase, DS/DC e referência. |
| DIAG-007 | Indisponibilidade | ESCALA_RULES 149 | Integração | Crítica | Deve identificar serviço durante ausência. |
| DIAG-008 | Restrição | ESCALA_RULES 42-44 | Integração | Crítica | Deve identificar restrição violada. |
| DIAG-009 | Equidade | ESCALA_RULES 150 | Integração | Média | Deve apresentar desvios sem inventar limiares. |
| DIAG-010 | Após geração | ESCALA_RULES 151 | Integração | Alta | Diagnóstico deve executar após geração. |
| DIAG-011 | Após edição | ESCALA_RULES 151 | Integração | Alta | Edição manual recalcula diagnóstico afetado. |
| DIAG-012 | Antes de validar | ESCALA_RULES 151 | Validação | Crítica | Erros impedem validação. |
| DIAG-013 | Antes de publicar | ESCALA_RULES 152 | Validação | Crítica | Diagnóstico essencial deve ser reexecutado. |
| DIAG-014 | Aviso autorizado | ESCALA_RULES 144, 155-157 | Auditoria | Alta | Autorização deve ficar registada. |

---

## 25. Testes de Auditoria

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| AUDIT-001 | Criação | ESCALA_RULES 156 | Auditoria | Alta | Criação funcional relevante deve gerar auditoria. |
| AUDIT-002 | Alteração | ESCALA_RULES 156-157 | Auditoria | Alta | Alteração deve guardar valor anterior e novo. |
| AUDIT-003 | Desativação | ESCALA_RULES 156, 162 | Auditoria | Alta | Desativação deve ficar registada. |
| AUDIT-004 | Edição manual | ESCALA_RULES 156-157 | Auditoria | Crítica | Deve registar célula, utilizador, motivo e valores. |
| AUDIT-005 | Override | ESCALA_RULES 19, 156 | Auditoria | Crítica | Override deve conter confirmação e motivo. |
| AUDIT-006 | Geração | ESCALA_RULES 156 | Auditoria | Alta | Geração deve ser auditada. |
| AUDIT-007 | Validação | ESCALA_RULES 156 | Auditoria | Alta | Validação deve ser auditada. |
| AUDIT-008 | Publicação | ESCALA_RULES 156 | Auditoria | Alta | Publicação deve ser auditada. |
| AUDIT-009 | Créditos | ESCALA_RULES 156 | Auditoria | Alta | FF/FC devem ser auditadas. |
| AUDIT-010 | Exportação | ESCALA_RULES 156, 171 | Auditoria | Média | Exportação deve criar registo. |
| AUDIT-011 | Configurações | ESCALA_RULES 156 | Auditoria | Alta | Alterações de configuração devem ser auditadas. |
| AUDIT-012 | Valor anterior | ESCALA_RULES 157 | Auditoria | Alta | Valor anterior deve estar disponível. |
| AUDIT-013 | Valor novo | ESCALA_RULES 157 | Auditoria | Alta | Valor novo deve estar disponível. |
| AUDIT-014 | Motivo | ESCALA_RULES 157 | Auditoria | Alta | Motivo deve ser obrigatório quando aplicável. |
| AUDIT-015 | Data | ESCALA_RULES 157 | Auditoria | Alta | Data e hora devem ser registadas. |
| AUDIT-016 | Utilizador | ESCALA_RULES 157 | Auditoria | Alta | Utilizador deve ser registado. |
| AUDIT-017 | Tentativa de alterar auditoria | ESCALA_RULES 158 | Segurança | Crítica | Registos não podem ser editados pela interface normal. |

---

## 26. Testes de Autenticação e Permissões

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| AUTH-001 | Comandante | ESCALA_RULES 182-183 | Segurança | Crítica | Perfil Comandante pode executar ações autorizadas. |
| AUTH-002 | Editor | ESCALA_RULES 184 | Segurança | Alta | Editor só executa ações expressamente autorizadas. |
| AUTH-003 | Consulta | ESCALA_RULES 185 | Segurança | Alta | Consulta não pode alterar escala. |
| AUTH-004 | Acesso sem autenticação | ESCALA_RULES 186-187 | Segurança | Crítica | Rotas protegidas devem exigir autenticação. |
| AUTH-005 | Palavra-passe com hash | ESCALA_RULES 186 | Segurança | Crítica | Password nunca em texto simples. |
| AUTH-006 | Operação não autorizada | ESCALA_RULES 182-185 | Segurança | Crítica | Deve bloquear e apresentar mensagem segura. |
| AUTH-007 | Sessão | ESCALA_RULES 187 | Segurança | Alta | Sessão deve respeitar regras configuradas. |
| AUTH-008 | Logout | ESCALA_RULES 186-187 | Segurança | Alta | Logout invalida sessão. |
| AUTH-009 | CSRF | ESCALA_RULES 194 | Segurança | Crítica | Operações POST/PATCH/DELETE devem proteger CSRF. |
| AUTH-010 | Alteração de permissões | ESCALA_RULES 182-186 | Auditoria | Alta | Deve exigir perfil autorizado e auditoria. |

---

## 27. Testes de Eliminação e Preservação

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| DELETE-001 | Desativar militar | ESCALA_RULES 161-162 | Funcional | Alta | Militar deixa de ser considerado no futuro e mantém histórico. |
| DELETE-002 | Eliminar militar sem histórico | ESCALA_RULES 163 | Funcional | Média | Pode ser permitido com confirmação reforçada se integridade estiver preservada. |
| DELETE-003 | Bloquear eliminação com histórico | ESCALA_RULES 163 | Validação | Crítica | Deve impedir eliminação definitiva. |
| DELETE-004 | Limpar células automáticas | ESCALA_RULES 203 | Funcional | Alta | Apenas automáticas desbloqueadas podem ser limpas. |
| DELETE-005 | Preservar células manuais | ESCALA_RULES 203 | Regressão | Crítica | Células manuais não podem ser limpas sem confirmação explícita. |
| DELETE-006 | Limpar intervalo | ESCALA_RULES 188-190 | Segurança | Alta | Operação ampla exige confirmação e backup quando aplicável. |
| DELETE-007 | Limpar militar | ESCALA_RULES 161-163 | Segurança | Alta | Não pode apagar histórico associado. |
| DELETE-008 | Limpar rascunho | ESCALA_RULES 209-210 | Funcional | Alta | Deve preservar versões publicadas/fechadas. |
| DELETE-009 | Confirmação reforçada | ESCALA_RULES 163 | Segurança | Alta | Ação destrutiva exige confirmação clara. |
| DELETE-010 | Auditoria e recuperação | ESCALA_RULES 155-159, 192 | Auditoria | Alta | Deve existir auditoria e possibilidade de reconstrução histórica. |

---

## 28. Testes da Base de Dados e Migrações

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| DBMIG-001 | Base de testes separada | ESCALA_RULES 49, 196 | Migração | Crítica | Testes nunca usam `instance/escala.db`. |
| DBMIG-002 | Ausência de `drop_all()` na base real | ESCALA_RULES 189 | Segurança | Crítica | Código não pode executar `drop_all()` na base real. |
| DBMIG-003 | Migração inicial | DATA_MODEL 47 | Migração | Alta | Deve criar apenas tabelas da fase aprovada. |
| DBMIG-004 | Atualização | ESCALA_RULES 189 | Migração | Alta | Atualização estrutural deve usar migração. |
| DBMIG-005 | Downgrade apenas em teste | CODING_STANDARDS 11 | Migração | Média | Downgrade não deve pôr dados reais em risco. |
| DBMIG-006 | Preservação de dados | ESCALA_RULES 188-190 | Migração | Crítica | Migração não pode apagar histórico. |
| DBMIG-007 | Falha de migração | CODING_STANDARDS 49 | Migração | Alta | Falha deve preservar estado anterior ou ser documentada. |
| DBMIG-008 | Backup antes de migração | ESCALA_RULES 190 | Migração | Alta | Antes de risco real deve existir backup. |
| DBMIG-009 | Chaves estrangeiras | DATA_MODEL 42 | Migração | Alta | Relações devem restringir eliminações perigosas. |
| DBMIG-010 | Dados históricos | DATA_MODEL 40-42 | Migração | Crítica | Histórico não deve ser eliminado por cascata indevida. |
| DBMIG-011 | Índices | DATA_MODEL 43 | Migração | Média | Índices definidos devem existir. |
| DBMIG-012 | Unicidade | DATA_MODEL 43 | Migração | Alta | Restrições únicas devem impedir duplicados. |

---

## 29. Testes de Dados Fictícios

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| FAKE-001 | Não criar militares | ESCALA_RULES 164 | Regressão | Crítica | Arranque/geração não cria militares fictícios. |
| FAKE-002 | Não criar equipas | ESCALA_RULES 164 | Regressão | Crítica | Equipas A-E só existem se criadas/confirmadas na base de testes ou pelo utilizador. |
| FAKE-003 | Não criar escalas | ESCALA_RULES 164 | Regressão | Crítica | Sem ação explícita, não há escalas fictícias. |
| FAKE-004 | Não criar indisponibilidades | ESCALA_RULES 164 | Regressão | Crítica | Não devem surgir ausências demonstrativas. |
| FAKE-005 | Não criar FF | ESCALA_RULES 164 | Regressão | Crítica | FF só surge com origem real/teste controlada. |
| FAKE-006 | Não criar FC | ESCALA_RULES 164 | Regressão | Crítica | FC só surge com origem aprovada. |
| FAKE-007 | Não criar serviços fictícios | ESCALA_RULES 164-165 | Regressão | Crítica | Apenas códigos estruturais oficiais podem ser criados. |
| FAKE-008 | Sem painéis simulados | ESCALA_RULES 177-178 | Interface | Alta | Dashboard não mostra números simulados. |

---

## 30. Testes de Exportação

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| EXPORT-001 | PDF | ESCALA_RULES 167-168 | Exportação | Alta | PDF deve representar versão selecionada. |
| EXPORT-002 | Excel | ESCALA_RULES 167, 169 | Exportação | Alta | Excel deve preservar estrutura mensal. |
| EXPORT-003 | A3 | ESCALA_RULES 168 | Exportação | Média | PDF mensal deve ser adequado a A3. |
| EXPORT-004 | Mês | ESCALA_RULES 168-170 | Exportação | Alta | Deve indicar mês correto. |
| EXPORT-005 | Ano | ESCALA_RULES 168-170 | Exportação | Alta | Deve indicar ano correto. |
| EXPORT-006 | Versão | ESCALA_RULES 170 | Exportação | Crítica | Não pode misturar versões. |
| EXPORT-007 | Estado | ESCALA_RULES 170 | Exportação | Alta | Deve indicar rascunho/validada/publicada/encerrada. |
| EXPORT-008 | Legenda | ESCALA_RULES 172 | Exportação | Alta | Deve incluir siglas relevantes. |
| EXPORT-009 | Códigos | ESCALA_RULES 172-174 | Exportação | Alta | Códigos devem coincidir com escala selecionada. |
| EXPORT-010 | Acentos | ESCALA_RULES 195 | Exportação | Alta | Caracteres portugueses devem ser preservados. |
| EXPORT-011 | UTF-8 | ESCALA_RULES 195 | Exportação | Alta | Ficheiros textuais devem manter UTF-8. |
| EXPORT-012 | Nome do ficheiro | ESCALA_RULES 171 | Exportação | Média | Nome deve identificar mês, versão e formato. |
| EXPORT-013 | Registo da exportação | ESCALA_RULES 171 | Auditoria | Alta | Deve guardar utilizador, data, tipo e resultado. |
| EXPORT-014 | Versão selecionada | ESCALA_RULES 170 | Regressão | Crítica | Exportar versão antiga não usa dados atuais por engano. |
| EXPORT-015 | Ausência de mistura entre versões | ESCALA_RULES 170 | Regressão | Crítica | Linhas/células devem pertencer à mesma versão. |

---

## 31. Testes de Interface

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| UI-001 | Segoe UI | ESCALA_RULES 176 | Interface | Média | Interface deve usar Segoe UI salvo indisponibilidade técnica. |
| UI-002 | Uso moderado de negrito | ESCALA_RULES 176-177 | Interface | Baixa | Negrito limitado ao essencial. |
| UI-003 | Seleção de mês | ESCALA_RULES 179 | Interface | Alta | Vista mensal deve permitir selecionar mês. |
| UI-004 | Mês anterior | ESCALA_RULES 179 | Interface | Média | Navegação para mês anterior deve manter contexto. |
| UI-005 | Mês seguinte | ESCALA_RULES 179 | Interface | Média | Navegação para mês seguinte deve manter contexto. |
| UI-006 | Vista mensal | ESCALA_RULES 179 | Interface | Alta | Militares em linhas, dias em colunas e códigos em células. |
| UI-007 | Indicadores manuais | ESCALA_RULES 181 | Interface | Alta | Atribuições manuais devem ser distinguíveis. |
| UI-008 | Mensagens de erro | ESCALA_RULES 143-145 | Interface | Alta | Erros devem ser claros e não expor detalhes técnicos. |
| UI-009 | Confirmações destrutivas | ESCALA_RULES 163, 188-190 | Interface | Alta | Ações destrutivas exigem confirmação compreensível. |
| UI-010 | Ausência de dados simulados | ESCALA_RULES 177-178 | Interface | Alta | Interface não pode apresentar indicadores fictícios. |
| UI-011 | Responsividade mínima | CODING_STANDARDS 37 | Interface | Média | Páginas principais devem ser legíveis em ecrã comum. |
| UI-012 | Legibilidade em A3 | ESCALA_RULES 168 | Exportação | Média | Exportação/vista para impressão deve ser legível. |

---

## 32. Testes de UTF-8

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| UTF8-001 | Interface com acentos | ESCALA_RULES 195 | Interface | Alta | Textos como Serviço, Aplicação e Compensação devem aparecer corretamente. |
| UTF8-002 | Nomes portugueses | ESCALA_RULES 195 | Integração | Alta | João, Gonçalo e Lourinhã devem ser preservados. |
| UTF8-003 | Base de dados | ESCALA_RULES 195 | Integração | Alta | Persistência em base de testes preserva UTF-8. |
| UTF8-004 | Logs | ESCALA_RULES 193, 195 | Validação | Média | Logs técnicos não devem corromper acentos. |
| UTF8-005 | PDF | ESCALA_RULES 168, 195 | Exportação | Alta | PDF deve preservar acentos. |
| UTF8-006 | Excel | ESCALA_RULES 169, 195 | Exportação | Alta | Excel deve preservar acentos. |
| UTF8-007 | CSV | ESCALA_RULES 195 | Exportação | Média | CSV, se existir, deve usar codificação compatível com UTF-8. |

---

## 33. Testes de Backup e Recuperação

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| BACKUP-001 | Criação de backup | ESCALA_RULES 190 | Funcional | Alta | Operação de risco deve criar backup antes de executar. |
| BACKUP-002 | Identificação | ESCALA_RULES 191 | Validação | Média | Backup deve incluir data, versão e identificação. |
| BACKUP-003 | Conteúdo | ESCALA_RULES 191 | Validação | Alta | Deve incluir base/configurações necessárias. |
| BACKUP-004 | Integridade | ESCALA_RULES 192 | Validação | Alta | Verificação deve confirmar ficheiro íntegro. |
| BACKUP-005 | Recuperação | ESCALA_RULES 192 | Funcional | Alta | Restauro deve exigir confirmação e preservar estado anterior quando aplicável. |
| BACKUP-006 | Confirmação | ESCALA_RULES 192 | Segurança | Alta | Restauro não deve executar sem confirmação. |
| BACKUP-007 | Falha | CODING_STANDARDS 49 | Validação | Alta | Falha deve ser registada e não deixar estado incoerente. |
| BACKUP-008 | Auditoria | ESCALA_RULES 155-157 | Auditoria | Alta | Backup/restauro devem ser auditados. |
| BACKUP-009 | Preservação de versão | ESCALA_RULES 209-210 | Regressão | Alta | Versões publicadas/encerradas devem ser preservadas. |

---

## 34. Testes de Desempenho

Não são definidos limites rígidos de tempo sem aprovação funcional/técnica. Os valores máximos aceitáveis devem ser aprovados antes da entrada em produção.

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| PERF-001 | 25 militares | CODING_STANDARDS 40 | Desempenho | Média | Operações principais devem permanecer utilizáveis com 25 militares. |
| PERF-002 | 50 militares | CODING_STANDARDS 40 | Desempenho | Média | Validar geração, diagnóstico e vista mensal com 50 militares. |
| PERF-003 | 100 militares | CODING_STANDARDS 40 | Desempenho | Média | Avaliar comportamento sem fixar limite rígido. |
| PERF-004 | 1 mês | CODING_STANDARDS 40 | Desempenho | Média | Gerar/abrir escala de um mês. |
| PERF-005 | 12 meses de histórico | CODING_STANDARDS 40 | Desempenho | Média | Equidade deve consultar histórico sem consultas excessivas. |
| PERF-006 | 5 anos de histórico | CODING_STANDARDS 40 | Desempenho | Baixa | Avaliar histórico longo antes de produção. |
| PERF-007 | Geração | CODING_STANDARDS 40 | Desempenho | Média | Medir geração com dados realistas. |
| PERF-008 | Diagnóstico e exportação | CODING_STANDARDS 40 | Desempenho | Média | Medir diagnóstico completo e exportação. |
| PERF-009 | Abertura da vista mensal | CODING_STANDARDS 37, 40 | Desempenho | Média | Vista mensal deve carregar de forma utilizável. |

---

## 35. Testes de Regressão

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| REG-001 | Estrutura de regressão | ESCALA_RULES 206 | Regressão | Crítica | Cada bug corrigido deve registar erro original, causa, versão afetada, teste criado, resultado antes, resultado depois e versões em que continua validado. |
| REG-002 | Fase 6 para Fase 1 | ESCALA_RULES 197 | Regressão | Crítica | Caso real de segunda-feira seguida de sábado/domingo deve permanecer coberto. |
| REG-003 | Manuais sobrevivem à regeneração | ESCALA_RULES 203 | Regressão | Crítica | Edição manual confirmada deve manter-se após regeneração. |
| REG-004 | Sem dados fictícios | ESCALA_RULES 164 | Regressão | Crítica | Correções não podem introduzir seeds automáticos na base real. |

---

## 36. Casos Reais Prioritários

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| REAL-001 | Equipa folga segunda e volta sábado/domingo | ESCALA_RULES 10-11, 197 | Regressão | Crítica | Fase 6 deve ser seguida pela Fase 1 sem reinício semanal. |
| REAL-002 | Disponibilidade 08:00-14:00 e noite excecional | ESCALA_RULES 42-44 | Funcional | Alta | Exceção noturna não elimina restrição diária geral. |
| REAL-003 | Falta de patrulheiros e recurso a SEC/SI | ESCALA_RULES 6-7, 24 | Integração | Alta | Recurso deve ser justificado e explicado. |
| REAL-004 | Trabalho em feriado gera FF pendente | ESCALA_RULES 85-94 | Integração | Crítica | Crédito nasce pendente e preserva serviço real. |
| REAL-005 | Trabalho em DS/DC preserva ciclo | ESCALA_RULES 18, 77-84, 212 | Validação | Alta | Ciclo não muda; compensação fica pendente se regra incompleta. |
| REAL-006 | Alteração manual sobrevive à regeneração | ESCALA_RULES 203 | Regressão | Crítica | Célula manual fica protegida. |
| REAL-007 | Ronda iniciada à sexta-feira | ESCALA_RULES 212 | Validação | Alta | Marcar `PENDENTE DE DECISÃO FUNCIONAL`. |
| REAL-008 | Ronda ao sábado | ESCALA_RULES 212 | Validação | Alta | Marcar `PENDENTE DE DECISÃO FUNCIONAL`. |
| REAL-009 | Mês com indisponibilidades extensas | ESCALA_RULES 32-41 | Integração | Alta | Deve diagnosticar faltas e não inventar militares. |
| REAL-010 | Escala sem efetivo para 9 mínimos | ESCALA_RULES 23-24 | Validação | Crítica | Deve bloquear/avisar, explicar faltas e candidatos excluídos. |

---

## 36-A. Casos da Grelha Mensal v0.7

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| GRID-001 | Seletor mensal responde | ESCALA_RULES 179 | UI | Alta | `/escala` apresenta seleção de mês e ano sem criar dados automaticamente. |
| GRID-002 | Mês vazio não é criado automaticamente | ESCALA_RULES 164, 188-190 | Funcional | Crítica | Abrir `/escala/<year>/<month>` mostra botão de criação controlada e não insere registos por GET. |
| GRID-003 | Criação controlada de mês | DATA_MODEL ScheduleMonth | Funcional | Crítica | POST de criação cria `ScheduleMonth` em `DRAFT` e `ScheduleVersion` número 1 com origem `INITIAL`. |
| GRID-004 | Unicidade de mês | DATA_MODEL ScheduleMonth | Modelo | Crítica | Não é possível criar dois meses com o mesmo ano e mês. |
| GRID-005 | DS/DC dinâmico | ESCALA_RULES 9-18 | Integração | Crítica | Grelha usa `CycleCalculator` e histórico de equipa por dia, sem persistir DS/DC. |
| GRID-006 | Indisponibilidade prevalece visualmente | ESCALA_RULES 32-41, 77-84 | Integração | Alta | Indisponibilidade confirmada aparece como código principal, preservando ciclo subjacente. |
| GRID-007 | Restrições como indicador | ESCALA_RULES 42-45 | Integração | Alta | Restrição aplicável aparece como indicador/tooltip e não substitui código principal. |
| GRID-008 | Sem geração operacional | Pedido v0.7 | Regressão | Crítica | Página da grelha não expõe geração AT/PO/PT, distribuição ou edição livre. |
| GRID-009 | Sem tabela de atribuições | Pedido v0.7 | Base de dados | Crítica | v0.7 não cria `assignments` nem `schedule_assignments`. |

---

## 36-B. Casos da Edição Manual v0.8

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| MANUAL-001 | Criar atribuição manual | ESCALA_RULES 18, 180-181 | Funcional | Crítica | Guardar código manual em versão `DRAFT` cria `Assignment` com origem `MANUAL` e evento `CREATED`. |
| MANUAL-002 | Bloqueio por defeito | ESCALA_RULES 3.4, 181 | Funcional | Alta | A célula manual fica protegida quando marcada como bloqueada. |
| MANUAL-003 | Alteração bloqueada exige desbloqueio | ESCALA_RULES 18, 203 | Regressão | Crítica | A tentativa de alterar célula bloqueada falha até existir desbloqueio. |
| MANUAL-004 | Limpeza preserva histórico | ESCALA_RULES 155-158 | Auditoria | Crítica | Limpar célula cria evento `CLEARED` e volta a mostrar o estado dinâmico. |
| MANUAL-005 | Override explícito | ESCALA_RULES 18-19, 144 | Validação | Crítica | Conflito ultrapassável só grava com confirmação de override e motivo. |
| MANUAL-006 | BM bloqueia override normal | ESCALA_RULES 35 | Segurança | Crítica | Baixa médica confirmada impede atribuição operacional sem exceção funcional documentada. |
| MANUAL-007 | Manual preserva camada subjacente | ESCALA_RULES 179-181 | Integração | Alta | Código manual prevalece visualmente e mantém DS/DC, indisponibilidade e restrições no contexto. |
| MANUAL-008 | Versões não editáveis bloqueiam | Pedido v0.8 | Estado | Crítica | `VALIDATED`, `PUBLISHED`, `CLOSED` e `NOT_GENERATED` não aceitam edição normal. |
| MANUAL-009 | Sem geração automática | Pedido v0.8 | Regressão | Crítica | Edição manual não seleciona militares, não cria AT/PO/PT automático, FF ou FC. |

---

## 36-C. Casos do Diagnóstico Inicial v0.9

| ID | Título | Regra de origem | Tipo | Prioridade | Procedimento e resultado esperado |
| --- | --- | --- | --- | --- | --- |
| DIAG-001 | Execução vazia | ESCALA_RULES 143-145 | Serviço | Alta | Diagnóstico de versão sem atribuições devolve informação e não altera a escala. |
| DIAG-002 | Persistência da execução | Pedido v0.9 | Base de dados | Crítica | Executar diagnóstico cria `DiagnosticRun` e `DiagnosticIssue`, preservando execuções anteriores. |
| DIAG-003 | Referência de ciclo em falta | ESCALA_RULES 12, 148 | Ciclo | Crítica | Patrulheiro com equipa sem referência gera erro de configuração/ciclo. |
| DIAG-004 | Serviço em DS | ESCALA_RULES 18 | Ciclo | Alta | Atribuição manual em dia DS gera aviso e preserva o ciclo subjacente. |
| DIAG-005 | Indisponibilidade confirmada | ESCALA_RULES 32-41, 149 | Indisponibilidade | Crítica | Atribuição manual sobre indisponibilidade confirmada é diagnosticada. |
| DIAG-006 | Override existente | ESCALA_RULES 155-158 | Auditoria | Alta | Override fundamentado aparece como informação/aviso sem remover a atribuição. |
| DIAG-007 | Descanso parcial | ESCALA_RULES 19 | Descanso | Alta | AT/PO consecutivos com menos de oito horas geram aviso. |
| DIAG-008 | Cobertura parcial | ESCALA_RULES 146 | Cobertura | Média | Contagem manual AT/PO é informativa e não seleciona candidatos. |
| DIAG-009 | Rotas de diagnóstico | Pedido v0.9 | Interface | Alta | Página, execução, filtros e detalhe respondem sem criar dados fictícios. |
| DIAG-010 | Caso real prioritário | Pedido v0.9 | Integração | Crítica | PO2 manual em DS com indisponibilidade e override gera diagnósticos esperados e não cria FF/FC. |

---

## 37. Matriz de Rastreabilidade

| Secção do ESCALA_RULES.md | Domínio | Casos | Estado |
| --- | --- | --- | --- |
| 3, 50-58 | Determinismo, seleção e equidade | EQUITY-001 a EQUITY-012, GEN-015, GEN-016 | coberto |
| 5-8, 46-49, 159-163 | Militares, grupos e equipas | MIL-001 a MIL-015, SECSI-001 a SECSI-009, CMD-001 a CMD-003 | coberto |
| 9-18, 197 | Ciclo, DS e DC | CYCLE-001 a CYCLE-016, DSDC-001 a DSDC-009, REAL-001 | coberto |
| 19, 147, 199 | Descanso mínimo | REST-001 a REST-013 | coberto |
| 20-29, 146, 198 | Cobertura, AT, PO e PT | COVERAGE-001 a COVERAGE-014, PT-001 a PT-011 | coberto |
| 30-31 | Código principal e adicionais | MANUAL-002, SPECIAL-007 a SPECIAL-010, SECSI-006 | parcialmente coberto |
| 32-45, 149-150, 200 | Indisponibilidades e restrições | RESTR-001 a RESTR-011, UNAV-001 a UNAV-018 | coberto |
| 77-84, 202, 212 | FC e compensações | FC-001 a FC-013, REAL-005, CMD-010 | pendente |
| 85-94, 201 | FF | FF-001 a FF-020, REAL-004 | coberto |
| 95-103 | Serviços remunerados | REM-001 a REM-010 | parcialmente coberto |
| 143-152 | Diagnósticos | DIAG-001 a DIAG-014 | coberto |
| 155-158 | Auditoria | AUDIT-001 a AUDIT-017 | coberto |
| 164-165, 177-178 | Dados fictícios e interface sem simulações | FAKE-001 a FAKE-008 | coberto |
| 167-175, 205 | Exportações e legenda | EXPORT-001 a EXPORT-015 | coberto |
| 176-181, 195 | Interface e UTF-8 | UI-001 a UI-012, UTF8-001 a UTF8-007 | coberto |
| 182-187, 194 | Autenticação, permissões e segurança | AUTH-001 a AUTH-010 | coberto |
| 188-192 | Base de dados, migrações e backups | DBMIG-001 a DBMIG-012, BACKUP-001 a BACKUP-009 | coberto |
| 206-208 | Regressão e aceitação | REG-001 a REG-004, REAL-001 a REAL-010 | coberto |

---

## 38. Critérios de Aprovação por Versão

* **Infraestrutura:** Application Factory, configuração, base de testes separada, logs, rotas básicas e testes iniciais.
* **Gestão de militares:** casos MIL e autenticação mínima aplicável.
* **Equipas:** pertença, histórico e referências de ciclo.
* **Ciclo:** casos CYCLE e DSDC críticos aprovados.
* **Indisponibilidades:** casos UNAV e RESTR críticos aprovados.
* **Grelha mensal:** UI, estados e preservação de dados.
* **Edição manual:** MANUAL e REGEN críticos aprovados.
* **Diagnóstico:** DIAG críticos aprovados.
* **Geração automática:** GEN, COVERAGE, REST, CYCLE, DSDC e EQUITY críticos aprovados.
* **FF:** FF críticos aprovados.
* **FC:** apenas após decisões funcionais pendentes.
* **Remunerados:** REM críticos aprovados e regras finalizadas.
* **Exportação:** EXPORT e UTF8 críticos aprovados.
* **Versão 1.0 operacional:** regras críticas cobertas, testes aprovados, auditoria, backup, exportações e aceitação manual.

---

## 39. Critério Final de Aceitação

A aplicação só pode ser considerada pronta para utilização real quando:

* regras críticas estão cobertas;
* testes passam;
* não existem erros bloqueantes;
* migrações foram validadas;
* backup foi testado;
* dados fictícios não são criados;
* alterações manuais são preservadas;
* ciclo foi validado em vários anos;
* FF e FC mantêm histórico;
* auditoria funciona;
* exportações foram verificadas;
* o responsável funcional realizou aceitação manual.

---

## Matérias Pendentes de Decisão Funcional

Devem permanecer bloqueadas ou marcadas como `PENDENTE DE DECISÃO FUNCIONAL`:

* aquisição e utilização automática de FC;
* compensações por trabalho em DS ou DC;
* regras completas da Ronda;
* regras completas do CR;
* regras completas do Serviço de Pronto;
* relação completa entre Ronda e CR;
* limites rígidos de desempenho antes de produção;
* compatibilidades detalhadas de serviços especiais ainda não formalizadas.

---

## 39-B. Casos da Geração Automática Inicial v1.0

Casos automatizados implementados na v1.0:

| ID | Caso | Domínio | Resultado esperado |
|---|---|---|---|
| GEN-001 | Geração AT/PO inicial | GEN/COVERAGE | AT1, AT2, AT3, PO1, PO2 e PO3 são preenchidos quando há efetivo elegível. |
| GEN-002 | Preservação manual | MANUAL | Atribuição manual existente não é substituída e conta para cobertura. |
| GEN-003 | Exclusão de CMD | GEN/STATE | CMD nunca recebe AT/PO. |
| GEN-004 | Patrulheiros antes de SEC/SI | GEN/EQUITY | SEC/SI não são usados quando patrulheiros elegíveis chegam. |
| GEN-005 | SEC/SI por insuficiência | GEN/EQUITY | SEC/SI podem ser usados quando patrulheiros elegíveis não chegam. |
| GEN-006 | Indisponibilidades | UNAV | Confirmadas e planeadas excluem candidatos automáticos. |
| GEN-007 | Restrições individuais | RESTR | Restrições aplicáveis excluem candidatos automáticos. |
| GEN-008 | Descanso mínimo | REST | Exatamente 8h é válido e menos de 8h exclui. |
| GEN-009 | Determinismo | EQUITY | A mesma entrada mantém a mesma ordenação/saída. |
| GEN-010 | Estado da versão | STATE | Versões não `DRAFT` bloqueiam geração. |
| GEN-011 | Rotas | UI | POST de geração e detalhe respondem corretamente. |
| GEN-012 | Diagnóstico final | DIAG | A geração cria diagnóstico final associado. |

Não coberto por implementação nesta versão:

* PT;
* FF;
* FC;
* Ronda;
* CR;
* remunerados;
* exportações;
* regeneração de automáticos.

---

## 39-C. Casos da Regeneração Segura v1.1

Casos automatizados implementados na v1.1:

| ID | Caso | Domínio | Resultado esperado |
|---|---|---|---|
| REGEN-101 | Nova versão sequencial | REGEN/STATE | Regenerar cria versão nova, `DRAFT`, `SYSTEM` e ligada à origem. |
| REGEN-102 | Origem preservada | REGEN/MANUAL | A versão anterior e as suas atribuições permanecem intactas. |
| REGEN-103 | Automáticos antigos | REGEN/GEN | Atribuições `SYSTEM` antigas não são copiadas. |
| REGEN-104 | Manual desbloqueada | MANUAL | Manual desbloqueada é copiada com notas e estado. |
| REGEN-105 | Célula limpa | MANUAL | Célula limpa não reaparece como código ativo na nova versão. |
| REGEN-106 | Estados bloqueados | STATE | `PUBLISHED` e `CLOSED` não permitem regeneração. |
| REGEN-107 | VALIDATED como origem | STATE | `VALIDATED` pode originar nova versão `DRAFT` sem alterar a origem. |
| REGEN-108 | Rollback | REGEN | Falha antes do commit remove nova versão e cópias. |
| REGEN-109 | Comparação | REGEN | Comparação apresenta manuais, automáticos e diferenças. |
| REGEN-110 | Rotas | UI | Confirmação, POST e comparação respondem corretamente. |
| REGEN-111 | Caso real prioritário | UNAV/RESTR/GEN | Nova indisponibilidade altera a escolha na versão regenerada e preserva a versão 1. |

Não coberto por implementação nesta versão:

* regeneração destrutiva na mesma versão;
* PT;
* FF;
* FC;
* Ronda;
* CR;
* remunerados;
* exportações.

---

## 39-D. Casos de Otimização v1.2

Casos automatizados implementados na v1.2:

| ID | Caso | Domínio | Resultado esperado |
|---|---|---|---|
| PERF-101 | Geração sem explosão de queries | GEN/PERF | Geração com 25 militares fica abaixo de limite razoável de queries. |
| PERF-102 | Grelha sem query por célula | GRID/PERF | Grelha mensal usa carregamento em lote. |
| PERF-103 | Diagnóstico em lote | DIAG/PERF | Diagnóstico de versão gerada evita queries repetidas por atribuição. |

Critérios:

* limites de queries possuem margem ampla baseada nas medições da v1.2;
* os testes não usam tempos rígidos;
* a base real não é usada para desempenho;
* a equivalência funcional continua coberta pelos testes GEN, REGEN, DIAG, GRID e MANUAL existentes.

---

## 39-E. Casos da Geração Automática de PT v1.3

Casos automatizados implementados na v1.3:

| ID | Caso | Domínio | Resultado esperado |
|---|---|---|---|
| PT-101 | PT desativado por defeito | PT/GEN | Geração sem parâmetros explícitos não cria PT. |
| PT-102 | Parâmetros inválidos | PT/STATE | Duração inválida ou hora inicial ausente bloqueiam a execução. |
| PT-103 | PT após AT/PO completo | PT/COVERAGE | PT só é criado depois de AT/PO do dia estar completo. |
| PT-104 | Cobertura incompleta | PT/COVERAGE | Dia com AT/PO incompleto não recebe PT automático. |
| PT-105 | Manual conta para limite | PT/MANUAL | PT manual é preservado e desconta ao máximo diário. |
| PT-106 | Elegibilidade real prioritária | PT/DSDC/UNAV/RESTR/REST | DS/DC, indisponibilidade, restrição, descanso e CMD excluem PT automático. |
| PT-107 | Regeneração | PT/REGEN | PT automático antigo não é copiado, PT manual é preservado e PT automático é recalculado. |
| PT-108 | Rotas | PT/UI | Formulário aceita parâmetros PT e apresenta detalhe da execução. |
| PT-109 | Diagnóstico manual | PT/DIAG | PT manual sem horário/duração gera aviso. |
| PT-110 | Diagnóstico CMD | PT/DIAG | PT atribuído a CMD gera erro. |
| PT-111 | PT não obrigatório | PT/COVERAGE/DIAG | Ausência de PT é informação e não cobertura obrigatória. |
| PERF-104 | Performance com PT | PT/PERF | Geração com PT não reintroduz explosão de queries. |

Critérios:

* PT não entra no total mínimo diário de nove militares;
* os dados dos testes existem apenas na base de testes;
* não são criados FF, FC, Ronda, CR, remunerados ou exportações.

---

## 39-F. Casos da Gestão Funcional de FF v1.4

Casos automatizados implementados na v1.4:

| ID | Caso | Domínio | Resultado esperado |
|---|---|---|---|
| FF-101 | Feriado manual | FF/DB | Criar feriado não cria militares, escalas ou créditos automaticamente. |
| FF-102 | Crédito por serviço em feriado | FF/ASSIGNMENT | Serviço elegível em feriado cria crédito pendente e mantém o código real no feriado. |
| FF-103 | Idempotência | FF/DB | A mesma atribuição de origem não cria dois créditos FF. |
| FF-104 | Processamento explícito | FF/UI | Rota de processamento cria apenas créditos selecionados e exige confirmação em `DRAFT`. |
| FF-105 | Agendamento | FF/MANUAL | Agendar FF cria célula `FF` manual, bloqueada e ligada ao crédito. |
| FF-106 | Regeneração | FF/REGEN | Regeneração segura preserva a célula FF e a ligação ao mesmo crédito. |
| FF-107 | Cancelamento de agendamento | FF/AUDIT | Cancelar agendamento limpa logicamente as células ligadas e devolve o crédito a `PENDING`. |
| FF-108 | Bloqueios de calendário | FF/CYCLE/UNAV | FF não é agendada em `DS/DC` nem em indisponibilidade ativa. |
| FF-109 | Proteção de célula | FF/MANUAL | Limpeza genérica de célula ligada a crédito FF é bloqueada. |
| FF-110 | Diagnóstico FF | FF/DIAG | Diagnóstico deteta direito potencial não processado e célula `FF` sem crédito. |

Não coberto por implementação na v1.4:

* FC;
* Ronda;
* CR;
* remunerados;
* exportações operacionais;
* confirmação operacional diária geral de serviços executados.

---

## 39-G. Casos da Gestao Funcional de FC e FR v1.6

Casos automatizados implementados na v1.6:

| ID | Caso | Dominio | Resultado esperado |
|---|---|---|---|
| FC-101 | R/CR em dia util e fim de semana | FC/R/CR | R ou CR em dia util cria 1 FC; ao sabado/domingo cria 2 FC independentes de 480 minutos. |
| FC-102 | R/CR em feriado | FC/FF | R/CR em feriado nao cria FC e fica elegivel para processamento FF. |
| FC-103 | Decisao de comando | FC/CMD | FC discricionaria exige militar, data, unidades inteiras positivas e motivo obrigatorio. |
| FC-104 | Agendamento FC | FC/MANUAL | Agendar FC cria celula `FC` manual, bloqueada, com 480 minutos e ligada ao credito. |
| FC-105 | Bloqueios FC | FC/STATE/UNAV | Agendamento FC bloqueia celula ocupada, indisponibilidade ativa e versao nao `DRAFT`. |
| FC-106 | Expiracao e protecao | FC/EXPIRY | FC expira apos 31 de dezembro, mas agendamento protegido pode manter uso no ano seguinte. |
| FC-107 | Gozo automatico | FC/WORKFLOW | FC agendada apenas passa a `USED` automaticamente quando existe celula coerente em versao oficial. |
| FR-101 | Origem FR | FR/CYCLE | AT/PO/PT em `DS`/`DC` cria direito FR sem alterar o ciclo. |
| FR-102 | Deteccao de potenciais | FC/FR/DIAG | Versao com R/CR e AT/PO/PT em DS/DC apresenta potenciais FC/FR pendentes. |
| FR-103 | Agendamento e cancelamento FR | FR/MANUAL | Agendar FR cria celula `FR` ligada; cancelar agendamento devolve o direito a `PENDING`. |
| BAL-101 | Saldos separados | FF/FC/FR | Saldos FC e FR permanecem separados e nao somam entre si. |
| REGEN-101 | Preservacao | FC/FR/REGEN | Regeneracao preserva celulas FC/FR manuais e ligacoes aos direitos existentes. |
| DIAG-101 | Diagnostico FC/FR | FC/FR/DIAG | Diagnostico reporta potenciais nao processados e creditos agendados sem celula coerente. |
| ROUTE-101 | Rotas FC/FR | UI | Paginas `/fc`, `/fc/novo` e `/folgas-reagendadas` respondem com sucesso. |

Continuam fora da v1.6:

* geracao automatica de Ronda;
* geracao automatica de CR;
* remunerados;
* exportacoes operacionais;
* notificacoes;
* autenticacao completa.

---


## 39-H. Casos da Exportacao Operacional Excel v1.7

Casos automatizados implementados na v1.7:

| ID | Caso | Dominio | Resultado esperado |
|---|---|---|---|
| EXPORT-101 | Workbook operacional | EXPORT/EXCEL | A exportacao cria `.xlsx` com folhas `Escala Mensal`, `Legenda`, `Resumo` e `Diagnostico`. |
| EXPORT-102 | Versao selecionada | EXPORT/STATE | A exportacao usa a versao pedida e indica estado, numero, revisao e selo operacional. |
| EXPORT-103 | Alteracoes manuais | EXPORT/MANUAL | Quando existem atribuicoes manuais, a folha `Alteracoes Manuais` e criada. |
| EXPORT-104 | Diagnostico existente | EXPORT/DIAG | A folha `Diagnostico` usa apenas diagnostico persistido e nao executa novo diagnostico. |
| EXPORT-105 | Formula injection | EXPORT/SECURITY | Textos iniciados por `=`, `+`, `-` ou `@` sao exportados como texto seguro. |
| EXPORT-106 | Rota Excel | EXPORT/UI | `GET /escala/<year>/<month>/versoes/<version_id>/exportar/excel` devolve ficheiro XLSX. |
| EXPORT-107 | Base inalterada | EXPORT/DB | Exportar nao cria atribuicoes, diagnosticos, creditos, ficheiros persistentes ou dados ficticios. |
| EXPORT-108 | Versao oficial | EXPORT/STATE | Versao publicada selecionada aparece como `VERSAO OFICIAL`. |

Continuam fora da v1.7:

* exportacao PDF;
* registo persistente/auditoria funcional de exportacoes;
* geracao automatica de Ronda;
* geracao automatica de CR;
* remunerados;
* notificacoes;
* autenticacao completa.

---

## 39-I. Casos da Exportacao Operacional PDF A3 v1.8

Casos automatizados implementados na v1.8:

| ID | Caso | Dominio | Resultado esperado |
|---|---|---|---|
| PDF-101 | PDF operacional | EXPORT/PDF | A exportacao cria PDF em memoria com grelha mensal A3 landscape, legenda, resumo, diagnostico e alteracoes manuais quando existirem. |
| PDF-102 | Versao selecionada | EXPORT/STATE | A exportacao usa a versao pedida e indica estado, numero, revisao e selo operacional. |
| PDF-103 | Rota PDF | EXPORT/UI | `GET /escala/<year>/<month>/versoes/<version_id>/exportar/pdf` devolve `application/pdf` com nome seguro. |
| PDF-104 | Versao oficial | EXPORT/STATE | Versao publicada selecionada aparece como `VERSAO OFICIAL` e como versao oficial publicada. |
| PDF-105 | Paginacao | EXPORT/PERFORMANCE | Exportacao com muitas linhas pagina sem cortar a geracao e preserva o conteudo esperado. |
| PDF-106 | Base inalterada | EXPORT/DB | Exportar nao cria atribuicoes, diagnosticos, creditos, ficheiros persistentes ou dados ficticios. |

Continuam fora da v1.8:

* registo persistente/auditoria funcional de exportacoes;
* geracao automatica de Ronda;
* geracao automatica de CR;
* remunerados;
* notificacoes;
* autenticacao completa.

---

## 39-J. Casos do Teste Operacional v1.9

Casos automatizados implementados na v1.9:

| ID | Caso | Dominio | Resultado esperado |
|---|---|---|---|
| OP-101 | Controlo sem dados reais | OP/UI | `/controlo-operacional` responde e indica estado nao preparado quando nao existem militares reais. |
| OP-102 | Prontidao operacional | OP/VALIDATION | A validacao deteta ausencia de patrulheiros, patrulheiros sem equipa e equipas sem referencia atual. |
| OP-103 | Pre-visualizacao CSV | OP/IMPORT | Pre-visualizar CSV valido nao altera a base de dados. |
| OP-104 | Confirmacao obrigatoria | OP/IMPORT | Importacao sem confirmacao e bloqueada. |
| OP-105 | Idempotencia por NIM | OP/IMPORT | Reimportar o mesmo NIM nao duplica militares e preserva uma pertença atual coerente. |
| OP-106 | Teste nao publicavel | OP/STATE | Versao marcada como teste operacional nao pode ser publicada. |
| OP-107 | Arquivo e avaliacao | OP/STATE | Teste operacional pode ser avaliado e arquivado sem passar a `CLOSED`. |
| OP-108 | Exportacao assinalada | OP/EXPORT | Excel e PDF de teste operacional incluem `Teste_Operacional` no nome do ficheiro. |
| OP-109 | Conferencia de ciclo | OP/CYCLE | A pagina de conferencia calcula DS/DC a partir das referencias existentes, sem escrita. |

Continuam fora da v1.9:

* importacao generica de Excel;
* autenticacao, roles e permissoes multiutilizador;
* geracao automatica de Ronda;
* geracao automatica de CR;
* remunerados;
* afinacao automatica sem dados reais fornecidos.

---

**Fim do documento — TEST_CASES.md**
