# Normas de Desenvolvimento — Escala de Serviço

**Projeto:** Escala de Serviço
**Documento:** `CODING_STANDARDS.md`
**Versão:** 1.0
**Estado:** Normativo
**Aplicável a:** Codex, programadores e outros assistentes de desenvolvimento
**Responsável funcional:** Comandante do Posto Territorial

---

## 1. Finalidade

Este documento define as normas obrigatórias para desenvolver, corrigir, testar e evoluir a aplicação Escala de Serviço.

O objetivo é impedir que uma alteração:

* modifique regras operacionais sem autorização;
* elimine dados;
* quebre funcionalidades existentes;
* crie militares ou escalas fictícias;
* introduza comportamentos não solicitados;
* torne a aplicação mais difícil de manter;
* prejudique a geração da escala;
* destrua alterações manuais;
* comprometa a auditoria;
* torne futuras alterações desnecessariamente complexas.

Estas normas aplicam-se a todas as intervenções no projeto, independentemente da dimensão da alteração.

---

## 2. Documentos obrigatórios

Antes de alterar código, devem ser consultados:

```text
AI_CONTEXT.md
docs/ESCALA_RULES.md
docs/ARCHITECTURE.md
docs/CODING_STANDARDS.md
docs/DATA_MODEL.md
docs/TEST_CASES.md
docs/CHANGELOG.md
```

Quando algum destes documentos ainda não existir, essa ausência deve ser identificada.

### 2.1. Ordem de autoridade

Em caso de conflito, aplica-se a seguinte ordem:

1. instrução atual e explícita do utilizador;
2. `docs/ESCALA_RULES.md`;
3. `docs/ARCHITECTURE.md`;
4. `docs/CODING_STANDARDS.md`;
5. `docs/DATA_MODEL.md`;
6. `docs/TEST_CASES.md`;
7. `AI_CONTEXT.md`;
8. comportamento atual do código;
9. suposições do programador ou assistente.

O código existente não prevalece sobre uma regra operacional documentada.

Quando o código contradiz o `ESCALA_RULES.md`, deve ser tratado como erro.

---

## 3. Regra fundamental

O Codex não pode inventar regras operacionais.

Quando uma situação não estiver definida:

1. não assumir uma solução definitiva;
2. não criar automatismos arbitrários;
3. manter a funcionalidade manual, quando possível;
4. identificar claramente a regra em falta;
5. registar a necessidade de decisão;
6. aguardar definição funcional antes de automatizar.

O sistema deve ser conservador perante regras incompletas.

---

## 4. Âmbito de cada alteração

Cada intervenção deve ter um objetivo principal claramente identificado.

Não devem ser implementadas várias funcionalidades grandes na mesma alteração.

Exemplos de alterações que devem ser separadas:

* gestão de militares;
* gestão de equipas;
* cálculo do ciclo;
* geração de AT e PO;
* serviços remunerados;
* sistema de FF;
* auditoria;
* exportação;
* autenticação;
* reformulação visual completa.

Uma alteração pode incluir pequenas tarefas auxiliares indispensáveis ao objetivo principal.

Não deve incluir melhorias sem relação direta apenas porque foram identificadas durante o trabalho.

---

## 5. Processo obrigatório antes de programar

Antes de alterar qualquer ficheiro, deve ser feita uma análise do projeto.

A análise deve identificar:

* estrutura atual;
* tecnologias utilizadas;
* ponto de entrada da aplicação;
* modelos afetados;
* rotas afetadas;
* serviços afetados;
* templates afetados;
* JavaScript afetado;
* testes existentes;
* migrações existentes;
* dependências relevantes;
* possíveis riscos;
* compatibilidade com dados atuais.

O Codex deve procurar reutilizar a arquitetura existente antes de criar novos módulos.

Não deve substituir uma solução funcional sem explicar a necessidade.

---

## 6. Plano de implementação

Antes de uma alteração relevante, deve existir um plano curto e objetivo contendo:

1. problema a resolver;
2. comportamento esperado;
3. ficheiros previstos;
4. alterações na base de dados;
5. testes necessários;
6. riscos;
7. forma de testar manualmente.

O plano não deve incluir funcionalidades não solicitadas.

Depois da análise, o Codex deve executar o trabalho sem pedir confirmações desnecessárias quando o pedido já estiver claro.

---

## 7. Alterações pequenas e controladas

As alterações devem ser feitas com o menor impacto razoável.

Deve ser evitado:

* reescrever ficheiros completos sem necessidade;
* substituir módulos estáveis;
* renomear muitas pastas durante uma correção pequena;
* alterar interfaces públicas sem necessidade;
* remover campos já utilizados;
* modificar estilos de páginas não relacionadas;
* atualizar dependências sem justificação;
* fazer refatorações extensas juntamente com uma nova funcionalidade.

Uma refatoração grande deve ser tratada como tarefa própria.

---

## 8. Preservação de funcionalidades

Nenhuma funcionalidade existente pode ser removida, desativada ou simplificada sem autorização explícita.

Antes de alterar um módulo existente, deve ser verificado:

* onde é utilizado;
* que rotas dependem dele;
* que templates o chamam;
* que testes o cobrem;
* que dados guarda;
* que outros serviços importam as suas funções.

Uma alteração não é considerada concluída apenas porque a nova funcionalidade funciona.

Também é necessário confirmar que as funcionalidades anteriores continuam operacionais.

---

## 9. Proibição de dados fictícios

É proibido criar automaticamente:

* militares fictícios;
* equipas fictícias;
* escalas fictícias;
* indisponibilidades fictícias;
* restrições fictícias;
* histórico fictício;
* serviços remunerados fictícios;
* alterações manuais fictícias.

É permitido criar configurações estruturais oficiais, como:

* códigos AT1, AT2 e AT3;
* códigos PO1, PO2 e PO3;
* PT;
* DS;
* DC;
* FF;
* FC;
* P;
* R;
* CR;
* tipos de restrição;
* tipos de indisponibilidade;
* estados da escala.

Dados de teste devem existir apenas em:

```text
tests/
```

ou numa base de dados exclusiva de testes.

Nunca podem ser introduzidos na base de dados real.

---

## 10. Proteção da base de dados

A base de dados real nunca deve ser apagada e recriada como método normal de atualização.

É proibido:

* eliminar `instance/escala.db`;
* executar `drop_all()` sobre a base de dados real;
* recriar todas as tabelas para adicionar um campo;
* substituir a base real por uma base de demonstração;
* limpar tabelas sem autorização;
* executar scripts destrutivos automaticamente no arranque.

Todas as alterações estruturais devem utilizar migrações.

---

## 11. Migrações

Qualquer alteração nos modelos que afete a estrutura da base de dados deve incluir uma migração.

O processo deve ser:

1. analisar os dados existentes;
2. criar backup;
3. alterar os modelos;
4. gerar a migração;
5. rever manualmente a migração;
6. garantir valores predefinidos seguros;
7. executar a migração;
8. confirmar que os dados antigos continuam acessíveis;
9. executar os testes;
10. atualizar o `CHANGELOG.md`.

Uma migração não pode presumir que a base está vazia.

### 11.1. Campos obrigatórios novos

Quando for adicionado um campo obrigatório a uma tabela com dados existentes, deve ser definido um processo de transição seguro.

Pode ser utilizado:

* valor temporário;
* campo inicialmente opcional;
* preenchimento controlado;
* segunda migração posterior.

Não se deve criar uma migração que falhe por existirem registos anteriores.

### 11.2. Remoção de campos

Um campo não deve ser eliminado imediatamente.

Processo recomendado:

1. deixar de o utilizar;
2. migrar os dados necessários;
3. confirmar que nenhuma funcionalidade depende dele;
4. manter durante um período de compatibilidade;
5. eliminar apenas numa versão posterior e autorizada.

---

## 12. Backups

Antes de qualquer operação potencialmente destrutiva, deve ser criada uma cópia da base de dados.

Operações que exigem backup:

* migrações;
* importações;
* restauros;
* eliminação em massa;
* correções diretas de dados;
* alteração da estrutura das escalas;
* alteração do cálculo de folgas;
* regeneração que possa substituir dados;
* atualização relevante da aplicação.

O backup deve ser criado numa pasta própria e não deve ser incluído no Git.

O Codex deve indicar claramente quando foi criado e onde ficou guardado.

---

## 13. Modelos e base de dados

Os modelos devem representar apenas dados e relações.

Não devem concentrar toda a lógica operacional.

Os modelos podem conter:

* campos;
* relações;
* propriedades simples;
* validações estruturais;
* métodos pequenos diretamente relacionados com a entidade.

As regras complexas devem ficar nos serviços.

### 13.1. Nomes dos campos

Os nomes internos devem ser claros e consistentes.

Exemplos:

```python
professional_number
full_name
functional_group
reference_date
reference_phase
start_datetime
end_datetime
manual_override
created_at
updated_at
```

Evitar nomes vagos como:

```python
data1
valor
tipo2
info
campo
estado_aux
```

### 13.2. Chaves primárias

As entidades principais devem utilizar identificadores internos.

O número profissional de um militar não deve ser utilizado como chave primária.

### 13.3. Relações

As relações devem possuir comportamento explícito.

Não deve ser configurada eliminação em cascata sobre dados históricos sem análise detalhada.

Eliminar ou desativar um militar não pode apagar:

* escalas anteriores;
* histórico;
* auditoria;
* FF;
* serviços remunerados;
* alterações manuais.

---

## 14. Serviços

A lógica operacional deve ficar em módulos de serviço.

Exemplos:

```text
cycle_calculator.py
schedule_generator.py
candidate_selector.py
rest_calculator.py
holiday_credit_service.py
manual_edit_service.py
schedule_state_service.py
```

Cada serviço deve possuir uma responsabilidade principal.

Evitar classes ou funções que façam simultaneamente:

* consultas;
* geração;
* validação;
* renderização HTML;
* exportação;
* escrita de logs;
* alteração de estado.

A lógica deve ser dividida em operações compreensíveis e testáveis.

---

## 15. Rotas Flask

As rotas devem ser simples.

Uma rota deve:

1. receber e validar o pedido;
2. verificar permissões;
3. chamar o serviço adequado;
4. tratar erros conhecidos;
5. devolver resposta ou renderizar template.

A rota não deve calcular:

* ciclos de folga;
* horas de descanso;
* prioridades de códigos;
* ordem de candidatos;
* saldo de FF;
* equilíbrio dos turnos.

### 15.1. Métodos HTTP

Utilizar:

* `GET` para consulta;
* `POST` para criação;
* `PUT` ou `PATCH` para alteração;
* `DELETE` para eliminação autorizada.

Uma rota `GET` nunca deve alterar dados.

### 15.2. Validação

Todos os dados recebidos devem ser validados no servidor.

A validação em JavaScript não substitui a validação no backend.

---

## 16. Templates

Os templates devem conter apenas lógica de apresentação simples.

É aceitável:

* mostrar ou ocultar elementos;
* iterar listas;
* apresentar estados;
* aplicar classes;
* formatar valores.

Não é aceitável:

* calcular o ciclo;
* escolher militares;
* determinar descansos;
* alterar prioridades;
* executar consultas complexas;
* decidir se uma escala é válida.

Os templates devem reutilizar componentes comuns.

---

## 17. JavaScript

O JavaScript deve ser utilizado apenas quando acrescentar valor real à interação.

Exemplos:

* edição da grelha;
* avisos de conflito;
* modais de confirmação;
* filtros;
* atualização parcial;
* atalhos de teclado;
* pré-visualização.

A lógica operacional principal nunca deve existir apenas no navegador.

Toda alteração enviada pelo JavaScript deve ser validada novamente pelo servidor.

O JavaScript deve:

* tratar erros;
* mostrar feedback;
* impedir pedidos duplicados;
* não perder alterações silenciosamente;
* não assumir que o servidor aceitou uma ação.

---

## 18. Interface do utilizador

A interface deve ser:

* simples;
* coerente;
* legível;
* adequada a ecrã de computador;
* orientada para utilização frequente;
* semelhante a ferramentas administrativas familiares.

Deve evitar:

* excesso de texto em negrito;
* excesso de cores;
* botões sem identificação;
* ações destrutivas pouco visíveis;
* mensagens técnicas incompreensíveis;
* janelas de confirmação em operações normais;
* elementos decorativos que prejudiquem a grelha.

### 18.1. Ações destrutivas

Devem ser claramente identificadas.

Exemplos:

* eliminar militar;
* remover indisponibilidade;
* remover alteração manual;
* regenerar escala;
* reabrir escala fechada;
* restaurar backup.

A confirmação deve explicar o efeito da ação.

### 18.2. Feedback

Depois de uma ação, a interface deve indicar:

* sucesso;
* erro;
* aviso;
* necessidade de confirmação;
* operação cancelada.

Não devem existir falhas silenciosas.

---

## 19. Regras operacionais no código

As regras operacionais devem ser identificáveis e testáveis.

Evitar números ou códigos sem contexto.

Em vez de:

```python
if count < 2:
    ...
```

Preferir:

```python
required_staff = service_code.required_staff

if assigned_count < required_staff:
    ...
```

Quando uma regra for fixa e normativa, deve existir:

* constante identificada;
* enum;
* configuração controlada;
* comentário com referência;
* teste correspondente.

A regra não deve ficar duplicada em vários locais.

---

## 20. Ciclo de folgas

O ciclo de folgas deve possuir uma única implementação oficial.

É proibido criar cálculos independentes do ciclo em:

* rotas;
* templates;
* exportações;
* JavaScript;
* diagnósticos;
* relatórios.

Todos os módulos devem utilizar o mesmo serviço.

O ciclo não pode ser calculado apenas através do número de semanas decorridas.

Deve respeitar os blocos sucessivos definidos no `ESCALA_RULES.md`.

Qualquer correção ao ciclo deve incluir testes de regressão.

---

## 21. Códigos de serviço

Os códigos devem ser tratados como entidades ou valores controlados.

Não devem ser repetidos arbitrariamente como texto em dezenas de ficheiros.

Evitar:

```python
if code == "AT1" or code == "AT2" or code == "AT3":
```

Quando possível, utilizar:

* categorias;
* coleções oficiais;
* métodos do serviço;
* enums;
* propriedades do código.

Exemplo conceptual:

```python
if service_code.category == ServiceCategory.ATTENDANCE:
    ...
```

A alteração da descrição visual não deve alterar o código interno.

---

## 22. Datas e horários

Devem ser utilizados objetos próprios de data e hora.

Não utilizar comparações textuais para determinar:

* ordem de datas;
* duração;
* descanso;
* mudança de dia;
* sobreposição;
* validade.

Os serviços que atravessam a meia-noite devem possuir data e hora finais corretas.

O cálculo do descanso deve usar:

```text
fim real do serviço anterior
início real do serviço seguinte
```

Não deve utilizar apenas o número do turno.

---

## 23. Determinismo

Com os mesmos dados de entrada e as mesmas configurações, a geração deve produzir o mesmo resultado.

É proibida a seleção aleatória não controlada.

Quando existir empate, deve ser aplicado um critério estável.

Exemplos:

* menor histórico;
* data do último serviço;
* número profissional;
* identificador interno;
* ordem alfabética.

O critério de desempate deve ser documentado.

---

## 24. Explicação das decisões automáticas

Sempre que possível, o sistema deve guardar a razão de cada nomeação automática.

Exemplos:

* militar disponível;
* sem indisponibilidades;
* descanso válido;
* menor total de AT2;
* maior intervalo desde o último turno noturno;
* desempate pelo número profissional.

Quando um candidato for excluído, deve ser possível identificar o motivo.

Isto é especialmente importante para:

* geração de AT;
* geração de PO;
* escolha de PT;
* remunerados;
* sugestões de FF;
* CR;
* serviços especiais.

---

## 25. Alterações manuais

As alterações do Comandante têm prioridade, mas devem ser auditáveis.

O código não pode:

* ignorar uma alteração manual;
* removê-la numa regeneração sem confirmação;
* substituir o valor silenciosamente;
* esconder os conflitos resultantes.

Cada alteração deve guardar:

* valor anterior;
* valor novo;
* utilizador;
* data e hora;
* origem;
* avisos;
* confirmação;
* justificação, quando aplicável.

---

## 26. Diagnósticos

Os validadores devem ser independentes sempre que possível.

Um validador deve:

* ter código próprio;
* possuir descrição;
* receber contexto;
* devolver resultados estruturados;
* não alterar a escala;
* não corrigir silenciosamente o problema.

A função de um validador é detetar e explicar.

A correção deve ser executada por serviço próprio ou pelo utilizador.

---

## 27. Tratamento de erros

Os erros conhecidos devem utilizar exceções específicas.

Exemplos:

```python
MissingTeamReferenceError
CycleCalculationError
ScheduleGenerationError
InvalidAssignmentError
DuplicateHolidayCreditError
ScheduleStateError
```

Não utilizar indiscriminadamente:

```python
except Exception:
    pass
```

É proibido ocultar erros sem registo.

Quando uma exceção geral for necessária:

* registar o erro completo nos logs;
* apresentar mensagem segura ao utilizador;
* não expor dados internos desnecessários;
* preservar o estado anterior.

---

## 28. Transações

Operações compostas devem utilizar transações.

Exemplos:

* geração mensal;
* regeneração;
* criação de nova versão;
* aplicação de várias alterações;
* criação de FF a partir de serviços executados;
* mudança de estado;
* importação;
* restauro.

Se uma parte crítica falhar, a operação deve ser revertida.

Não deve ficar uma escala parcialmente gerada sem identificação.

---

## 29. Auditoria e logs

Auditoria e logs possuem finalidades diferentes.

### Auditoria

Regista ações funcionais:

* quem alterou;
* o que alterou;
* quando;
* valor anterior;
* valor novo;
* motivo;
* confirmações.

### Logs

Registam funcionamento técnico:

* erros;
* exceções;
* arranque;
* desempenho;
* falhas de ficheiros;
* falhas de migrações;
* operações técnicas.

Um não substitui o outro.

---

## 30. Segurança

A aplicação deve seguir práticas mínimas de segurança.

Obrigatório:

* validação no servidor;
* proteção CSRF;
* palavras-passe com hash;
* controlo de permissões;
* consultas parametrizadas através do ORM;
* nomes de ficheiro seguros;
* restrição de tipos de ficheiro;
* proteção da pasta `instance`;
* proteção da base de dados;
* sessões seguras;
* mensagens de erro controladas.

Não guardar:

* palavras-passe em texto simples;
* chaves secretas no repositório;
* dados pessoais em logs sem necessidade;
* backups no GitHub.

---

## 31. Dependências

Uma nova biblioteca só deve ser adicionada quando:

* for necessária;
* estiver mantida;
* for compatível com a versão de Python;
* não existir solução adequada já instalada;
* não introduzir complexidade excessiva.

Ao adicionar uma dependência:

1. atualizar `requirements.txt`;
2. indicar a finalidade;
3. fixar versão quando adequado;
4. testar instalação limpa;
5. verificar licenciamento;
6. atualizar documentação.

Não atualizar todas as dependências durante uma correção não relacionada.

---

## 32. Estilo Python

O código Python deve seguir, tanto quanto possível:

* PEP 8;
* nomes claros;
* funções pequenas;
* type hints nas interfaces relevantes;
* docstrings em serviços complexos;
* imports organizados;
* ausência de código morto;
* ausência de duplicação desnecessária.

### 32.1. Nomes

Classes:

```python
ScheduleGenerator
CycleCalculator
HolidayCreditService
```

Funções e variáveis:

```python
calculate_next_block
available_candidates
reference_date
```

Constantes:

```python
MINIMUM_REST_HOURS
SUPPORTED_FUNCTIONAL_GROUPS
```

### 32.2. Funções

Uma função deve possuir uma responsabilidade clara.

Evitar funções com:

* centenas de linhas;
* muitos níveis de indentação;
* demasiados parâmetros;
* consultas, validação e gravação misturadas;
* efeitos secundários inesperados.

---

## 33. Type hints

As interfaces dos serviços devem utilizar anotações de tipo quando acrescentarem clareza.

Exemplo:

```python
def calculate_team_days_off(
    team_id: int,
    start_date: date,
    end_date: date,
) -> list[DayOffBlock]:
    ...
```

Não é necessário adicionar type hints de forma mecânica a todo o código antigo durante uma alteração pequena.

---

## 34. Comentários e documentação

Os comentários devem explicar:

* por que existe uma decisão;
* que regra operacional está a ser aplicada;
* que limitação está a ser contornada;
* que risco deve ser evitado.

Não devem apenas repetir o código.

Mau exemplo:

```python
# Incrementa o contador
counter += 1
```

Melhor exemplo:

```python
# O segundo dia dos blocos de dois dias recebe DC, conforme ESCALA_RULES.md.
```

As funções complexas devem possuir docstrings.

---

## 35. Testes obrigatórios

Nenhuma regra crítica deve ser alterada sem testes.

Devem existir testes para:

* ciclo de folgas;
* DS e DC;
* continuidade entre fases;
* cobertura mínima;
* descanso de oito horas;
* restrições;
* indisponibilidades;
* PT;
* FF;
* remunerados;
* alterações manuais;
* estados da escala;
* auditoria;
* preservação de dados;
* regeneração.

### 35.1. Erros corrigidos

Cada bug corrigido deve originar um teste de regressão.

O teste deve:

1. reproduzir o erro anterior;
2. falhar antes da correção;
3. passar depois da correção;
4. permanecer no projeto.

### 35.2. Isolamento

Os testes devem utilizar:

* base temporária;
* fixtures próprias;
* diretórios temporários;
* configuração de testes.

Nunca devem utilizar a base real.

### 35.3. Nomes dos testes

Os nomes devem explicar o comportamento.

Exemplo:

```python
def test_phase_six_is_followed_by_phase_one_weekend():
    ...
```

Evitar:

```python
def test_cycle_3():
    ...
```

---

## 36. Testes manuais

Além dos testes automáticos, cada alteração visual ou funcional deve incluir passos de teste manual.

Exemplo:

```text
1. Abrir Militares.
2. Criar um militar real.
3. Confirmar que não é criada automaticamente nenhuma equipa fictícia.
4. Editar o militar.
5. Recarregar a página.
6. Confirmar que os dados permanecem guardados.
```

Os passos devem ser concretos e adequados ao utilizador.

---

## 37. Qualidade da interface

Depois de alterar uma página, deve ser verificado:

* carregamento;
* alinhamento;
* responsividade mínima;
* menus;
* botões;
* mensagens;
* campos obrigatórios;
* erros;
* tabelas vazias;
* grandes quantidades de dados;
* caracteres portugueses;
* datas no formato português.

A página não deve funcionar apenas com dados de demonstração.

Deve ser testada também sem registos.

---

## 38. Exportações

PDF, Excel e CSV devem utilizar os mesmos dados da escala apresentada.

Não devem existir três implementações independentes da lógica da escala.

As exportações devem receber uma representação já preparada da versão da escala.

Uma exportação não pode:

* alterar dados;
* recalcular folgas de forma diferente;
* regenerar a escala;
* ignorar alterações manuais;
* utilizar uma versão diferente da selecionada.

---

## 39. Compatibilidade

As alterações devem preservar, sempre que possível:

* dados atuais;
* URLs existentes;
* nomes dos campos utilizados;
* configurações;
* exports anteriores;
* estrutura dos backups;
* funcionalidades estáveis.

Quando uma incompatibilidade for inevitável, deve existir:

* justificação;
* migração;
* instruções;
* backup;
* plano de reversão;
* atualização documental.

---

## 40. Desempenho

A aplicação deve evitar:

* uma consulta por célula;
* uma consulta por militar dentro de cada dia;
* carregar histórico repetidamente;
* recalcular todo o mês após uma pequena alteração;
* executar diagnóstico completo quando basta validar uma célula;
* escrever ficheiros durante cada consulta.

Para gerar uma escala, os dados principais devem ser carregados de forma eficiente e reutilizados durante o processo.

A otimização nunca deve tornar a lógica incompreensível ou alterar resultados.

---

## 41. Acessibilidade e legibilidade

A interface deve manter:

* contraste suficiente;
* texto legível;
* indicação que não dependa apenas da cor;
* botões identificados;
* navegação por teclado quando razoável;
* mensagens de erro associadas aos campos;
* tamanhos adequados para utilização diária.

As cores da escala devem possuir legenda.

---

## 42. Git

Não devem ser incluídos no repositório:

```text
instance/escala.db
instance/backups/
exports/
logs/
.env
__pycache__/
.pytest_cache/
*.pyc
```

Devem ser incluídos:

* código;
* migrações;
* testes;
* documentação;
* ficheiros de configuração de exemplo;
* `requirements.txt`;
* `.gitignore`.

### 42.1. Commits

Cada commit deve representar uma alteração coerente.

Mensagens recomendadas:

```text
feat: adicionar gestão de equipas
fix: corrigir continuidade da fase 6 para a fase 1
test: adicionar regressão do ciclo de folgas
docs: atualizar regras da FF
refactor: separar cálculo do descanso
```

Não utilizar mensagens vagas como:

```text
alterações
update
fix
final
teste
```

---

## 43. Versionamento

As versões devem seguir uma progressão controlada.

Exemplo:

```text
v0.1 — Estrutura base
v0.2 — Gestão de militares
v0.3 — Gestão de equipas
v0.4 — Ciclo de folgas
v0.5 — Indisponibilidades
```

Cada versão deve atualizar:

* `docs/CHANGELOG.md`;
* `AI_CONTEXT.md`;
* testes relevantes;
* documentação alterada.

Não alterar o número da versão sem registar o conteúdo da alteração.

---

## 44. CHANGELOG

O `CHANGELOG.md` deve indicar:

* versão;
* data;
* funcionalidades adicionadas;
* erros corrigidos;
* alterações de base de dados;
* migrações;
* incompatibilidades;
* instruções adicionais.

Exemplo:

```text
## v0.4.1 — 2026-07-27

### Corrigido
- Corrigido o avanço da Fase 6 para a Fase 1.
- O ciclo deixa de avançar por semanas civis.

### Testes
- Adicionado teste de regressão para a folga de segunda-feira seguida do bloco de sábado e domingo.
```

---

## 45. Atualização do AI_CONTEXT.md

Depois de uma alteração relevante, o `AI_CONTEXT.md` deve ser atualizado com:

* versão atual;
* funcionalidade concluída;
* ficheiros principais;
* decisões tomadas;
* migrações executadas;
* testes existentes;
* problemas conhecidos;
* próximo passo recomendado.

O documento deve refletir o estado real do projeto.

Não deve descrever funcionalidades ainda não implementadas como concluídas.

---

## 46. Critérios de conclusão

Uma alteração só é considerada concluída quando:

1. o comportamento solicitado foi implementado;
2. as regras operacionais foram respeitadas;
3. os dados existentes foram preservados;
4. a aplicação inicia sem erros;
5. as migrações foram criadas, quando necessárias;
6. os testes relevantes passam;
7. foi efetuado teste manual;
8. não foram criados dados fictícios;
9. a documentação foi atualizada;
10. foram indicados os ficheiros alterados;
11. foram dadas instruções de teste;
12. foram identificadas limitações ainda existentes.

“Código escrito” não significa “funcionalidade concluída”.

---

## 47. Relatório obrigatório após cada alteração

No final de cada intervenção, o Codex deve apresentar:

### Resumo

Descrição curta do que foi implementado.

### Ficheiros alterados

Lista dos ficheiros criados, alterados ou removidos.

### Base de dados

Indicação de:

* modelos alterados;
* migração criada;
* backup necessário;
* comando de migração.

### Testes

Indicação de:

* testes adicionados;
* testes executados;
* resultado.

### Como testar

Passos manuais concretos.

### Compatibilidade

Confirmação do que foi preservado.

### Limitações

Aspetos que ainda não foram implementados ou validados.

### Próximo passo recomendado

Apenas uma próxima etapa principal.

---

## 48. Proibições absolutas

O Codex não pode:

1. criar militares fictícios;
2. criar escalas fictícias na base real;
3. apagar a base de dados;
4. executar `drop_all()` na base real;
5. remover funcionalidades sem autorização;
6. alterar o ciclo de folgas;
7. alterar prioridades operacionais;
8. ignorar o `ESCALA_RULES.md`;
9. esconder conflitos;
10. eliminar alterações manuais;
11. apagar histórico;
12. eliminar auditoria;
13. escolher militares aleatoriamente;
14. modificar dados durante uma exportação;
15. usar a base real nos testes;
16. alterar vários módulos grandes sem necessidade;
17. atualizar dependências sem justificação;
18. guardar segredos no repositório;
19. afirmar que algo foi testado quando não foi;
20. considerar uma tarefa concluída quando a aplicação não inicia.

---

## 49. Comportamento perante falhas

Quando não for possível concluir uma alteração, o Codex deve:

1. preservar o estado funcional anterior;
2. não deixar ficheiros parcialmente quebrados;
3. reverter alterações inseguras;
4. indicar o ponto exato da falha;
5. explicar o que foi concluído;
6. explicar o que ficou por concluir;
7. indicar os erros ou testes que falharam;
8. não inventar resultados.

Uma conclusão parcial segura é preferível a uma alteração extensa e instável.

---

## 50. Regra final

O desenvolvimento deve ser previsível, documentado, testável e reversível.

O Codex deve atuar como executor técnico das decisões do utilizador.

Não deve atuar como responsável pelas regras operacionais.

Sempre que uma decisão técnica possa alterar o funcionamento da escala, deve prevalecer a solução que:

1. respeite o `ESCALA_RULES.md`;
2. preserve os dados;
3. preserve funcionalidades;
4. mantenha a auditoria;
5. permita intervenção manual do Comandante;
6. produza comportamento determinístico;
7. possa ser testada e revertida.
