# Regras Operacionais — Escala de Serviço

**Projeto:** Escala de Serviço  
**Documento:** ESCALA_RULES.md  
**Versão:** 1.0  
**Estado:** Documento Normativo  
**Responsável funcional:** Comandante do Posto Territorial

---

# 1. Finalidade

Este documento define todas as regras operacionais que regem a aplicação Escala de Serviço.

É o documento mais importante do projeto.

Todo o comportamento da aplicação deve resultar exclusivamente das regras aqui descritas.

Caso exista qualquer divergência entre:

- código existente;
- decisões técnicas;
- arquitetura;
- modelos da base de dados;
- documentação;

prevalece sempre este documento.

O código implementa estas regras.

O código nunca cria regras novas.

---

# 2. Objetivos da aplicação

A aplicação tem como objetivo permitir ao Comandante:

- gerir o efetivo;
- gerar automaticamente a escala mensal;
- editar manualmente qualquer serviço;
- controlar férias e ausências;
- controlar serviços remunerados;
- controlar compensações;
- manter histórico completo;
- produzir exportações;
- manter auditoria integral.

A aplicação deve minimizar trabalho administrativo sem retirar ao Comandante o controlo total da escala.

---

# 3. Princípios fundamentais

Todas as decisões automáticas obedecem aos seguintes princípios.

## 3.1 Segurança

Nenhuma decisão automática pode colocar um militar numa situação operacional ilegal.

---

## 3.2 Determinismo

Com os mesmos dados de entrada deve sempre ser produzido exatamente o mesmo resultado.

Nunca deve existir aleatoriedade.

---

## 3.3 Transparência

Todas as decisões automáticas devem poder ser explicadas.

Sempre que possível deve existir registo da razão pela qual determinado militar foi escolhido.

---

## 3.4 Preservação

Uma alteração manual efetuada pelo Comandante tem prioridade sobre qualquer geração automática.

---

## 3.5 Auditoria

Todas as alterações relevantes devem ficar registadas.

---

## 3.6 Simplicidade

Sempre que existam duas soluções equivalentes deve ser escolhida a mais simples.

---

## 3.7 Equidade

A distribuição dos serviços deve ser equilibrada ao longo do tempo.

---

# 4. Organização do efetivo

Cada militar pertence a um grupo funcional.

Os grupos funcionais existentes são:

PATRULHEIRO

SEC

SI

CMD

Cada grupo possui regras próprias.

---

# 5. Patrulheiros

Os patrulheiros constituem o efetivo operacional principal.

Cada patrulheiro pertence obrigatoriamente a uma equipa operacional.

As equipas existentes são:

A

B

C

D

E

Cada patrulheiro pertence apenas a uma equipa de cada vez.

O histórico das mudanças de equipa deve ser preservado.

---

# 6. SEC

Os militares SEC trabalham normalmente:

Segunda-feira a sexta-feira

09:00 às 17:00

Folgam:

Sábado

Domingo

Podem ser chamados para executar serviços AT ou PO quando necessário.

Quando executam um desses serviços, esse serviço substitui o horário normal.

---

# 7. SI

Os militares SI seguem exatamente as mesmas regras do SEC.

---

# 8. CMD

O Comandante não executa:

AT

PO

PT

O Comandante pode executar:

P

R

CR

quando aplicável.

---

# 9. Equipas operacionais

As equipas operacionais seguem permanentemente um ciclo fixo de folgas.

Esse ciclo nunca depende do mês civil.

Nunca depende do número da semana.

Nunca depende do calendário.

Depende apenas da sequência contínua definida neste documento.

---

# 10. Ciclo oficial

O ciclo possui seis fases.

Fase 1

Folga:

Sábado

Domingo

Fase 2

Folga:

Sexta-feira

Fase 3

Folga:

Quinta-feira

Sexta-feira

Fase 4

Folga:

Quarta-feira

Quinta-feira

Fase 5

Folga:

Terça-feira

Quarta-feira

Fase 6

Folga:

Segunda-feira

Depois da Fase 6 recomeça obrigatoriamente na Fase 1.

Não existe qualquer outra sequência válida.

---

# 11. Continuidade

O ciclo nunca reinicia por começar um novo mês.

Nunca reinicia por começar um novo ano.

Nunca reinicia por mudança de comandante.

Nunca reinicia por geração de nova escala.

A continuidade é obrigatória.

---

# 12. Referência do ciclo

Cada equipa possui uma referência.

Essa referência contém:

equipa

data

fase

A partir dessa referência toda a sequência futura é calculada.

Alterar uma referência nunca elimina o histórico anterior.

---

# 13. Dias de folga

Os dias de folga utilizam dois códigos.

DS

DC

---

# 14. DS

DS significa:

Descanso Semanal.

É o primeiro dia do bloco de folga.

---

# 15. DC

DC significa:

Descanso Complementar.

É o segundo dia do bloco quando exista.

---

# 16. Blocos de um dia

Quando a fase possui apenas um dia de folga:

esse dia recebe DS.

Nunca recebe DC.

---

# 17. Blocos de dois dias

Quando existem dois dias consecutivos:

Primeiro dia:

DS

Segundo dia:

DC

Nunca podem ser invertidos.

---

# 18. Prioridade das folgas

As folgas do ciclo têm prioridade sobre qualquer serviço normal.

Só podem ser alteradas manualmente pelo Comandante.

Toda a alteração deve ficar registada.

---

# 19. Descanso mínimo

Entre dois serviços deve existir, por regra, um descanso mínimo de oito horas.

Qualquer violação deve gerar aviso.

Só pode ser autorizada manualmente.

Essa autorização deve ficar em auditoria.

# 20. Organização diária do serviço

A escala diária deve garantir a cobertura mínima dos serviços operacionais obrigatórios.

Os serviços principais são:

- AT1;
- AT2;
- AT3;
- PO1;
- PO2;
- PO3.

Os serviços adicionais apenas podem ser atribuídos depois de garantida a cobertura mínima obrigatória.

---

# 21. Serviço AT

AT corresponde ao serviço de atendimento.

Existem três turnos diários.

## 21.1 AT1

Horário:

00:00 às 08:00

Efetivo mínimo:

1 militar.

---

## 21.2 AT2

Horário:

08:00 às 16:00

Efetivo mínimo:

1 militar.

---

## 21.3 AT3

Horário:

16:00 às 00:00

Efetivo mínimo:

1 militar.

---

# 22. Serviço PO

PO corresponde ao serviço de patrulhamento ou policiamento operacional.

Existem três turnos diários.

## 22.1 PO1

Horário:

00:00 às 08:00

Efetivo mínimo:

2 militares.

---

## 22.2 PO2

Horário:

08:00 às 16:00

Efetivo mínimo:

2 militares.

---

## 22.3 PO3

Horário:

16:00 às 00:00

Efetivo mínimo:

2 militares.

---

# 23. Cobertura mínima diária

A cobertura mínima diária corresponde a:

- AT1: 1 militar;
- AT2: 1 militar;
- AT3: 1 militar;
- PO1: 2 militares;
- PO2: 2 militares;
- PO3: 2 militares.

Total mínimo diário:

9 militares.

A aplicação deve validar diariamente esta cobertura.

---

# 24. Falta de cobertura

Quando não seja possível garantir os mínimos obrigatórios, a aplicação não pode ocultar o problema.

Deve:

1. identificar o turno em falta;
2. identificar o número de militares em falta;
3. explicar as causas conhecidas;
4. apresentar os candidatos excluídos e respetivos motivos;
5. emitir diagnóstico visível;
6. permitir decisão manual do Comandante.

A aplicação não pode inventar militares para preencher faltas.

A aplicação não pode atribuir o mesmo militar a dois serviços incompatíveis no mesmo dia.

---

# 25. Prioridades gerais da geração

A geração automática obedece à seguinte ordem de prioridades:

1. garantir os mínimos operacionais obrigatórios;
2. respeitar indisponibilidades absolutas;
3. respeitar as folgas DS e DC;
4. respeitar o descanso mínimo;
5. respeitar restrições individuais;
6. preservar alterações manuais;
7. garantir equidade;
8. reduzir complexidade;
9. atribuir serviços adicionais apenas a militares sobrantes.

Quando duas prioridades entrem em conflito, prevalece a prioridade com número inferior.

---

# 26. Serviço PT

PT corresponde a patrulhamento ou serviço adicional atribuído apenas quando exista efetivo sobrante.

O PT nunca tem prioridade sobre:

- AT;
- PO;
- descanso;
- DS;
- DC;
- indisponibilidades;
- restrições obrigatórias.

---

# 27. Duração do PT

O PT pode ter:

- 8 horas;
- 6 horas.

A duração deve ficar expressamente registada.

A aplicação não deve assumir automaticamente a duração quando não esteja configurada.

---

# 28. Atribuição do PT

O PT apenas pode ser atribuído depois de:

1. preencher todos os serviços AT;
2. preencher todos os serviços PO;
3. validar o descanso mínimo;
4. validar todas as indisponibilidades;
5. confirmar que o militar não está de folga;
6. confirmar que o militar não possui outro código incompatível nesse dia.

Quando não exista efetivo sobrante, não deve ser criado PT.

---

# 29. Prioridade reduzida do PT

O PT possui prioridade inferior aos restantes serviços operacionais obrigatórios.

A ausência de PT não constitui, por si só, falha de cobertura mínima.

A aplicação pode apresentar essa ausência como informação, mas não como erro crítico.

---

# 30. Regra de um código principal por dia

Cada militar deve possuir apenas um código principal por dia.

São códigos principais, entre outros:

- AT1;
- AT2;
- AT3;
- PO1;
- PO2;
- PO3;
- PT;
- P;
- R;
- DS;
- DC;
- FF;
- FC;
- LF;
- LP;
- BM;
- LC;
- LN;
- DIL;
- TRIB;
- INQ.

Não podem coexistir dois códigos principais incompatíveis no mesmo dia.

---

# 31. Registos adicionais

Quando um militar execute uma atividade adicional compatível com o código principal, essa atividade deve ser registada separadamente.

Não deve substituir indevidamente o código principal.

A compatibilidade entre códigos e atividades adicionais deve estar explicitamente configurada.

---

# 32. Indisponibilidades absolutas

Uma indisponibilidade absoluta impede a atribuição de serviços operacionais no período abrangido.

São indisponibilidades absolutas, quando aplicáveis:

- LF;
- LP;
- BM;
- LC;
- LN;
- DIL;
- TRIB;
- INQ;
- outras ausências legalmente reconhecidas;
- restrições médicas incompatíveis;
- formação obrigatória incompatível com o turno;
- licença;
- baixa;
- férias;
- diligência;
- tribunal;
- inquérito.

A aplicação deve permitir acrescentar novos códigos de indisponibilidade sem alterar a lógica central.

---

# 33. LF

LF corresponde a licença para férias ou férias, conforme a nomenclatura operacional adotada.

Durante LF, o militar está indisponível para serviços incompatíveis.

A LF bloqueia a geração automática de AT, PO e PT.

---

# 34. LP

LP corresponde a uma licença ou ausência prevista na configuração da aplicação.

A sua designação completa deve estar registada na legenda oficial.

Durante LP, o militar não pode receber serviços incompatíveis.

---

# 35. BM

BM corresponde a baixa médica.

Durante BM, o militar está indisponível.

Não pode ser escalado para qualquer serviço operacional.

---

# 36. LC e LN

LC e LN correspondem a licenças ou situações de indisponibilidade definidas oficialmente.

Enquanto estiverem ativas, impedem serviços incompatíveis.

A aplicação não pode reinterpretar o seu significado sem atualização normativa.

---

# 37. DIL

DIL corresponde a diligência.

Quando a diligência ocupa todo o período relevante, o militar fica indisponível para serviço incompatível.

Quando possua horário parcial, devem ser considerados:

- hora de início;
- hora de fim;
- deslocação;
- descanso;
- compatibilidade com o serviço.

---

# 38. TRIB

TRIB corresponde a comparência em tribunal.

O militar deve ser considerado indisponível durante o período necessário.

A aplicação deve permitir registar:

- data;
- hora de início;
- hora de fim;
- local;
- tempo de deslocação, quando aplicável;
- observações.

---

# 39. INQ

INQ corresponde a inquérito ou diligência processual equivalente.

Devem ser aplicadas as mesmas regras de compatibilidade temporal utilizadas nas restantes diligências.

---

# 40. Indisponibilidades parciais

Uma indisponibilidade pode abranger:

- o dia completo;
- um intervalo horário;
- vários dias;
- um padrão recorrente.

A aplicação deve verificar a sobreposição real entre o período de indisponibilidade e o horário do serviço.

---

# 41. Sobreposição temporal

Existe conflito quando o horário do serviço e o período de indisponibilidade se sobrepõem.

Também pode existir conflito quando, apesar de não haver sobreposição direta, não seja possível cumprir o descanso mínimo.

---

# 42. Restrição horária individual

Um militar pode possuir uma restrição horária individual.

Exemplos:

- apenas disponível das 08:00 às 14:00;
- não disponível para turnos noturnos;
- disponível para um serviço noturno específico;
- não disponível em determinados dias da semana.

As restrições devem incluir:

- data de início;
- data de fim, quando exista;
- dias aplicáveis;
- hora inicial;
- hora final;
- natureza da restrição;
- observações;
- fundamento, quando necessário.

---

# 43. Restrições recorrentes

A aplicação deve permitir restrições recorrentes.

Exemplo:

- disponibilidade diária entre as 08:00 e as 14:00;
- disponibilidade adicional para serviço noturno de quinta-feira para sexta-feira.

Uma exceção positiva não elimina a restrição geral.

Deve ser registada como exceção expressa.

---

# 44. Hierarquia das restrições

Uma restrição absoluta prevalece sobre uma disponibilidade especial.

Uma disponibilidade especial apenas permite o serviço expressamente autorizado.

A aplicação não pode alargar automaticamente essa autorização a outros turnos.

---

# 45. Aptidões

Cada militar pode possuir aptidões ou qualificações específicas.

Exemplos:

- aptidão para CR;
- aptidão para determinado serviço;
- habilitação de condução;
- formação específica;
- restrição de função.

A geração deve respeitar as aptidões exigidas para cada serviço.

---

# 46. Militar ativo

Apenas militares ativos podem ser considerados pela geração.

Um militar ativo deve possuir:

- data de início válida;
- ausência de data de fim anterior ao dia da escala;
- estado funcional compatível.

---

# 47. Entrada e saída do efetivo

A data de início determina a partir de quando o militar pode ser escalado.

A data de fim determina até quando pode ser escalado.

A aplicação deve respeitar estas datas em cada dia do mês.

---

# 48. Modo real

No modo real, a aplicação utiliza todos os militares ativos.

Não deve existir limitação artificial do número de militares.

---

# 49. Modo de teste

No modo de teste, pode existir limitação controlada do número de militares.

O modo de teste deve:

- estar claramente identificado;
- usar base de dados separada;
- não alterar dados reais;
- não criar dados fictícios na base real;
- não ser confundido com o modo operacional.

---

# 50. Seleção de candidatos

Para cada serviço, a aplicação deve construir uma lista de candidatos elegíveis.

Antes da ordenação por equidade, deve excluir quem:

- não esteja ativo;
- esteja indisponível;
- esteja de DS ou DC;
- possua serviço incompatível;
- não cumpra o descanso;
- não possua aptidão necessária;
- tenha restrição incompatível;
- esteja fora do período de pertença ao efetivo;
- tenha alteração manual bloqueada.

---

# 51. Explicação das exclusões

Para cada candidato excluído, a aplicação deve conseguir indicar o motivo.

Exemplos:

- indisponível por LF;
- descanso inferior a oito horas;
- restrição horária;
- já possui PO2;
- dia de DS;
- sem aptidão para CR;
- militar inativo;
- alteração manual protegida.

---

# 52. Ordenação dos candidatos

Depois de aplicadas todas as exclusões, os candidatos elegíveis devem ser ordenados de forma determinística.

Devem ser considerados, por esta ordem:

1. menor carga do serviço em causa;
2. menor carga no período relevante;
3. menor número de turnos noturnos;
4. menor número de fins de semana trabalhados;
5. menor número de serviços consecutivos;
6. equilíbrio entre equipas;
7. antiguidade da última atribuição equivalente;
8. identificador estável para desempate técnico.

O último critério serve apenas para garantir determinismo.

Nunca deve ser usado sorteio.

---

# 53. Equidade

A equidade não significa igualdade matemática absoluta em cada mês.

Significa distribuição progressivamente equilibrada ao longo do tempo.

Devem ser considerados:

- serviços AT;
- serviços PO;
- PT;
- serviços noturnos;
- sábados;
- domingos;
- feriados;
- serviços remunerados;
- serviços especiais;
- cargas anteriores.

---

# 54. Equidade por serviço

A comparação deve ser feita, sempre que possível, entre militares elegíveis para o mesmo tipo de serviço.

Um militar que não pode executar determinado serviço não deve ser penalizado por ter menos atribuições desse serviço.

---

# 55. Equidade por equipa

A aplicação deve apresentar indicadores por equipa.

Deve ser possível consultar:

- número total de serviços;
- número de AT;
- número de PO;
- número de noites;
- número de fins de semana;
- DS e DC;
- ausências;
- distribuição por militar.

---

# 56. Histórico de equidade

A equidade deve considerar um período configurável.

Não deve depender apenas do mês que está a ser gerado.

O período deve ser suficientemente longo para evitar desequilíbrios recorrentes.

---

# 57. Alterações manuais e equidade

Um serviço atribuído manualmente deve contar para a equidade, salvo indicação normativa em contrário.

A origem manual não elimina o impacto real do serviço executado.

---

# 58. Dias consecutivos de trabalho

A aplicação deve acompanhar sequências consecutivas de trabalho.

Quando uma sequência seja excessiva ou operacionalmente desaconselhada, deve emitir alerta.

O limite rígido, caso exista, deve ser definido por configuração normativa e não inventado pelo motor.

---

# 59. Preferência pela simplicidade

Quando duas soluções cumpram todas as regras e apresentem equilíbrio semelhante, deve ser escolhida a solução mais simples.

São exemplos de simplicidade:

- evitar mudanças desnecessárias;
- evitar fragmentar equipas;
- reduzir alternâncias excessivas de horário;
- manter padrões compreensíveis;
- reduzir exceções.

---

# 60. Proibição de otimização opaca

A aplicação não deve utilizar um processo de otimização impossível de explicar ao utilizador.

Cada atribuição deve possuir fundamentação compreensível.
# 61. Serviço normal de SEC e SI

Os militares SEC e SI trabalham normalmente:

- de segunda-feira a sexta-feira;
- das 09:00 às 17:00.

O código do serviço normal deve ser configurável.

A representação visual pode utilizar a designação definida pelo Comandante.

---

# 62. Fins de semana de SEC e SI

Os militares SEC e SI folgam normalmente:

- sábado;
- domingo.

Estas folgas não seguem o ciclo A a E.

---

# 63. Recurso a SEC e SI

SEC e SI podem ser chamados para AT ou PO quando não exista cobertura suficiente com os patrulheiros elegíveis.

Antes de recorrer a SEC ou SI, a aplicação deve:

1. avaliar os patrulheiros disponíveis;
2. identificar a falta de cobertura;
3. verificar a compatibilidade funcional;
4. verificar restrições;
5. verificar descanso;
6. registar a razão da seleção.

---

# 64. Serviço operacional de SEC e SI

Quando SEC ou SI executam AT ou PO, o serviço operacional substitui o serviço normal desse período.

Não deve existir duplicação de códigos principais.

---

# 65. Prioridade de utilização de SEC e SI

A utilização de SEC e SI em serviços operacionais deve ocorrer apenas por necessidade.

Não deve ser usada como mecanismo normal de equilíbrio quando existam patrulheiros elegíveis suficientes.

---

# 66. Comandante

O Comandante possui regime próprio.

O Comandante não integra a geração automática de:

- AT;
- PO;
- PT.

---

# 67. Código P

P representa o serviço normal do Comandante ou função equivalente.

Aplica-se normalmente:

- de segunda-feira a sexta-feira.

O horário deve estar configurado de acordo com o regime em vigor.

---

# 68. Ronda

R representa serviço de ronda de 24 horas, quando aplicável.

A ronda apenas pode ser atribuída a militares autorizados.

Normalmente:

- Comandante;
- Segundo Comandante;
- outros expressamente autorizados.

---

# 69. CR

CR representa compensação, descanso ou código relacionado com o serviço de ronda, de acordo com a regra operacional definida.

A sua atribuição deve estar diretamente associada à ronda que a originou.

---

# 70. Registo da ronda

Cada ronda deve registar:

- militar;
- data e hora de início;
- data e hora de fim;
- origem da atribuição;
- compensação gerada;
- data prevista da compensação;
- estado;
- observações.

---

# 71. Ronda em dia útil

Quando a ronda se inicia num dia útil, deve ser considerada a regra de compensação aplicável.

Conforme definido operacionalmente:

- as primeiras oito horas podem coincidir com o serviço normal do dia;
- as horas adicionais geram a compensação prevista;
- deve ser criado o crédito correspondente quando aplicável.

A aplicação deve manter a ligação entre ronda e compensação.

---

# 72. Ronda iniciada à sexta-feira

Quando a ronda se inicia à sexta-feira e abrange período adicional para além do serviço normal:

- o período normal do dia é contabilizado;
- o período adicional é registado;
- pode ser gerada uma FC, conforme a regra aprovada.

A aplicação deve permitir validar esta situação sem alterar DS ou DC automaticamente.

---

# 73. Ronda ao sábado

Quando a ronda é executada num sábado que seria folga:

- deve ser registado que houve trabalho em dia de folga;
- deve ser criada a compensação aplicável;
- o direito adquirido deve ficar pendente até agendamento.

---

# 74. Compensação associada à ronda

A compensação da ronda não deve ser confundida com:

- DS;
- DC;
- FF;
- férias;
- baixa;
- licença.

Cada tipo de crédito deve ter origem e histórico próprios.

---

# 75. FC

FC corresponde a folga compensatória ou compensação equivalente decorrente de serviço que confira esse direito.

A FC deve possuir uma origem identificável.

Exemplos de origem:

- ronda;
- trabalho em dia de folga;
- serviço extraordinário;
- outra situação expressamente reconhecida.

---

# 76. Crédito de FC

Quando se constitui o direito a FC, deve ser criado um crédito.

O crédito deve conter:

- militar;
- tipo;
- origem;
- data de aquisição;
- quantidade;
- unidade;
- estado;
- referência ao serviço;
- observações.

---

# 77. Estados da FC

Uma FC pode possuir os seguintes estados:

- pendente;
- agendada;
- gozada;
- reagendada;
- cancelada.

O estado cancelado exige motivo e autorização.

---

# 78. FC pendente

Uma FC pendente representa um direito adquirido ainda não marcado.

Não ocupa automaticamente uma célula da escala.

Não substitui DS ou DC.

---

# 79. Agendamento de FC

Ao agendar uma FC, devem ser verificados:

- cobertura mínima;
- indisponibilidades;
- outras ausências;
- compatibilidade com o ciclo;
- saldo existente;
- autorização.

A FC não deve ser agendada automaticamente sem regra ou decisão autorizada.

---

# 80. Gozo de FC

Quando a FC é efetivamente gozada:

- deve ser assinalada na escala;
- o crédito deve passar a gozado;
- deve ficar registada a data efetiva;
- o saldo deve ser atualizado;
- a operação deve ficar em auditoria.

---

# 81. Reagendamento de FC

Uma FC agendada pode ser reagendada.

O histórico deve manter:

- data anterior;
- nova data;
- motivo;
- utilizador;
- data da alteração.

---

# 82. Cancelamento de FC

Cancelar uma FC agendada não deve eliminar o direito adquirido, salvo decisão expressamente fundamentada.

Quando o agendamento é cancelado mas o direito permanece, o estado deve regressar a pendente.

O estado cancelado do crédito apenas deve ser usado quando o próprio direito seja anulado por decisão válida.

---

# 83. FF

FF corresponde à folga compensatória adquirida por trabalho prestado num feriado.

A FF é um direito autónomo.

Não corresponde a DS.

Não corresponde a DC.

Não corresponde automaticamente a FC.

---

# 84. Aquisição da FF

Quando um militar presta serviço num feriado e esse serviço confere direito a FF, a aplicação deve criar um crédito de FF.

O crédito deve estar associado a:

- militar;
- feriado;
- serviço executado;
- data;
- turno;
- regra que originou o direito.

---

# 85. Código no dia do feriado

No dia do feriado, a célula da escala deve manter o código do serviço efetivamente executado.

Exemplos:

- AT1;
- AT2;
- AT3;
- PO1;
- PO2;
- PO3;
- PT;
- R;
- outro serviço autorizado.

Não deve ser colocado FF no próprio dia em substituição do serviço executado.

---

# 86. FF pendente

Depois de adquirida, a FF fica pendente.

Enquanto pendente:

- não ocupa uma célula da escala;
- não altera o ciclo;
- não substitui DS;
- não substitui DC;
- não desaparece no final do mês;
- transita para os meses seguintes.

---

# 87. Estados da FF

Uma FF pode possuir os estados:

- pendente;
- agendada;
- gozada;
- reagendada;
- cancelada.

A aplicação deve guardar o histórico completo das transições.

---

# 88. Agendamento da FF

A FF deve ser agendada posteriormente.

O agendamento deve considerar:

- disponibilidade do militar;
- cobertura mínima;
- necessidades do serviço;
- outras ausências;
- saldo pendente;
- autorização do Comandante.

---

# 89. FF agendada

Quando uma FF é agendada:

- o crédito passa a agendado;
- a data prevista fica registada;
- a escala apresenta FF nesse dia;
- deve existir ligação entre a célula e o crédito original.

---

# 90. FF gozada

A FF apenas passa a gozada quando o dia tiver efetivamente ocorrido e o gozo estiver confirmado.

Devem ficar registados:

- data prevista;
- data efetiva;
- utilizador que confirmou;
- data da confirmação.

---

# 91. Reagendamento da FF

A FF pode ser reagendada.

O histórico deve manter todas as datas anteriores.

Nunca deve ser apagada a data inicialmente prevista.

---

# 92. Cancelamento do agendamento da FF

Se o agendamento for cancelado e o direito se mantiver:

- a FF regressa a pendente;
- o saldo continua disponível;
- o histórico do cancelamento é preservado.

---

# 93. Cancelamento do direito de FF

O direito de FF só pode ser cancelado mediante decisão expressa e fundamentada.

Devem ficar registados:

- motivo;
- utilizador;
- data;
- documento de suporte, quando exista.

---

# 94. Feriados

A aplicação deve possuir registo de feriados.

Cada feriado deve conter:

- data;
- designação;
- âmbito;
- estado ativo;
- observações.

---

# 95. Âmbito dos feriados

Os feriados podem ser:

- nacionais;
- municipais;
- locais;
- institucionais, quando aplicável.

A elegibilidade para FF deve respeitar a regra configurada.

---

# 96. Alteração de feriados

Uma alteração à tabela de feriados não pode apagar direitos de FF já adquiridos.

Os créditos existentes preservam a data e a origem histórica.

---

# 97. Trabalho em DS ou DC

Quando um militar trabalha num dia originalmente destinado a DS ou DC:

- o serviço efetivamente executado deve ficar registado;
- a folga original deve permanecer no histórico;
- deve ser avaliada a compensação aplicável;
- deve ser criado crédito quando exista direito;
- a alteração deve ser auditada.

---

# 98. Preservação do ciclo após trabalho em folga

Trabalhar num dia de DS ou DC não desloca automaticamente todo o ciclo.

O ciclo oficial mantém-se.

A compensação é tratada separadamente.

---

# 99. Compensação nas indisponibilidades

Ao registar uma indisponibilidade que recaia sobre um dia de folga, a aplicação pode exigir a indicação de compensação, quando aplicável.

O campo de compensação deve permitir:

- não aplicável;
- pendente de decisão;
- gera crédito;
- não gera crédito;
- observação.

---

# 100. Saldo de créditos

A aplicação deve apresentar separadamente:

- saldo de FF;
- saldo de FC;
- outros créditos compensatórios.

Nunca deve juntar direitos diferentes num saldo indistinto.

---

# 101. Proibição de créditos sem origem

Nenhum crédito pode ser criado sem origem identificada.

A origem pode ser:

- serviço;
- feriado;
- ronda;
- alteração manual fundamentada;
- importação validada;
- decisão administrativa.

---

# 102. Ajustes manuais de saldo

Um ajuste manual de saldo deve exigir:

- valor anterior;
- valor novo;
- diferença;
- motivo;
- utilizador;
- data;
- observação;
- documento de suporte, quando aplicável.

---

# 103. Serviços remunerados

A aplicação deve permitir gerir serviços remunerados separadamente da escala ordinária.

Os remunerados não podem comprometer:

- serviço obrigatório;
- descanso;
- indisponibilidades;
- restrições;
- segurança operacional.

---

# 104. Preferências para remunerados

O militar pode indicar preferência ou disponibilidade para remunerados.

A preferência não constitui direito automático à atribuição.

---

# 105. Seleção para remunerados

A seleção deve considerar:

1. elegibilidade;
2. disponibilidade;
3. descanso;
4. aptidão;
5. conflito com escala normal;
6. equidade histórica;
7. preferências válidas;
8. critérios definidos pelo Comandante.

---

# 106. Equidade nos remunerados

A aplicação deve permitir consultar:

- número de remunerados por militar;
- horas;
- valores, quando registados;
- datas;
- recusas;
- indisponibilidades;
- critérios de seleção.

---

# 107. Explicação da seleção para remunerados

A aplicação deve guardar os candidatos considerados.

Para cada candidato, deve ser registado:

- elegível ou excluído;
- motivo;
- posição na ordenação;
- critérios relevantes;
- decisão final.

---

# 108. Separação financeira

Caso sejam registados valores financeiros, estes devem ficar separados da lógica operacional da escala.

A existência de remuneração não altera automaticamente as regras de descanso ou cobertura.
# 109. Serviços especiais

A aplicação deve permitir criar serviços especiais.

Um serviço especial pode incluir:

- designação;
- local;
- data;
- hora inicial;
- hora final;
- responsável;
- número de militares;
- aptidões necessárias;
- observações;
- estado.

---

# 110. Participantes em serviços especiais

Cada participante deve ser associado individualmente ao serviço especial.

A aplicação deve verificar:

- disponibilidade;
- descanso;
- conflito com escala;
- aptidão;
- restrições;
- pertença ao efetivo.

---

# 111. Compatibilidade de serviços especiais

Um serviço especial pode:

- substituir o serviço normal;
- coexistir como atividade adicional;
- ocupar apenas parte do dia.

A regra de compatibilidade deve ser definida expressamente.

---

# 112. Escala mensal

A escala é organizada por mês civil para efeitos de visualização, edição, validação e exportação.

A organização mensal não altera a continuidade do ciclo.

---

# 113. Seleção do mês

O utilizador deve poder escolher:

- mês;
- ano.

A seleção deve estar disponível através de controlo simples, como lista pendente ou seletor equivalente.

---

# 114. Navegação entre meses

A aplicação deve permitir:

- mês anterior;
- mês seguinte;
- mês atual;
- escolha direta de mês e ano.

A navegação não deve regenerar automaticamente a escala.

---

# 115. Estados da escala

Cada mês deve possuir um estado.

Estados mínimos:

- não gerada;
- rascunho;
- validada;
- publicada;
- encerrada.

---

# 116. Estado não gerada

Significa que ainda não existe uma versão operacional da escala para o mês.

Podem existir dados preparatórios.

---

# 117. Estado rascunho

Permite:

- geração;
- edição;
- alterações manuais;
- diagnóstico;
- correções;
- nova versão.

---

# 118. Estado validada

Significa que a escala foi revista e aprovada para publicação.

Alterações posteriores devem exigir registo e podem criar nova versão.

---

# 119. Estado publicada

Significa que a escala foi disponibilizada aos utilizadores autorizados.

Qualquer alteração deve ficar claramente identificada.

---

# 120. Estado encerrada

Significa que o período foi concluído e consolidado.

Uma escala encerrada não deve ser alterada livremente.

Uma reabertura deve exigir:

- autorização;
- motivo;
- registo de auditoria.

---

# 121. Versões da escala

Cada mês pode possuir várias versões.

Cada versão deve conter:

- número;
- data de criação;
- origem;
- estado;
- utilizador;
- motivo;
- relação com versão anterior.

---

# 122. Geração inicial

A geração inicial cria uma nova versão de rascunho.

Antes da geração, a aplicação deve validar:

- existência de militares ativos;
- equipas;
- referências do ciclo;
- códigos de serviço;
- cobertura configurada;
- indisponibilidades;
- restrições;
- feriados;
- dados mínimos necessários.

---

# 123. Pré-validação da geração

Se faltarem dados essenciais, a geração deve ser bloqueada.

A aplicação deve indicar exatamente o que falta.

Exemplos:

- equipa sem referência de ciclo;
- militar ativo sem equipa;
- código de serviço inexistente;
- cobertura não configurada;
- mês inválido.

---

# 124. Processo de geração

O processo recomendado é:

1. criar a grelha do mês;
2. identificar militares ativos por dia;
3. aplicar DS e DC;
4. aplicar indisponibilidades;
5. preservar registos manuais;
6. preencher serviços obrigatórios;
7. validar descanso;
8. validar cobertura;
9. distribuir PT apenas a sobrantes;
10. calcular indicadores;
11. executar diagnósticos;
12. guardar resultado;
13. guardar explicações.

---

# 125. Geração por fases

A geração deve ser modular.

Cada fase deve poder ser testada separadamente.

Não deve existir uma única função extensa responsável por todo o processo.

---

# 126. Registo da execução da geração

Cada geração deve guardar:

- data e hora;
- utilizador;
- mês;
- versão;
- parâmetros;
- resultado;
- avisos;
- erros;
- duração;
- número de atribuições;
- identificador técnico.

---

# 127. Determinismo da geração

A mesma versão dos dados de entrada deve produzir o mesmo resultado.

Se o resultado for diferente, a aplicação deve conseguir identificar qual dado mudou.

---

# 128. Regeneração

Regenerar significa voltar a executar o motor sobre uma escala existente.

A regeneração não pode apagar automaticamente alterações manuais.

---

# 129. Modos de regeneração

A aplicação deve distinguir, pelo menos:

- regenerar apenas células automáticas;
- completar apenas células vazias;
- recalcular diagnóstico;
- criar nova versão.

Não deve existir uma opção destrutiva disfarçada.

---

# 130. Proteção das alterações manuais

Uma célula alterada manualmente deve ficar marcada como protegida.

O motor automático não pode substituí-la sem ação explícita.

---

# 131. Desbloqueio de alteração manual

O Comandante pode desbloquear uma célula.

O desbloqueio deve ficar em auditoria.

Após desbloqueada, a célula pode voltar a ser gerida pelo motor automático.

---

# 132. Edição manual

O utilizador autorizado pode alterar uma atribuição.

A alteração deve validar:

- existência do militar;
- data;
- código;
- compatibilidade;
- descanso;
- cobertura;
- indisponibilidades;
- restrições.

---

# 133. Avisos na edição manual

A aplicação pode permitir uma alteração que origine aviso, quando o perfil possuir autorização.

Nesse caso deve:

- apresentar o risco;
- pedir confirmação;
- exigir motivo;
- guardar auditoria.

---

# 134. Erros bloqueantes

Existem situações que não devem ser ultrapassadas por edição normal.

Exemplos:

- militar inexistente;
- data fora do mês;
- código inválido;
- duplicação impossível;
- violação de integridade da base;
- atribuição a militar inativo fora do período.

---

# 135. Override manual

Um override é uma decisão expressa que ultrapassa um aviso operacional.

O override deve registar:

- utilizador;
- data;
- regra afetada;
- motivo;
- valor anterior;
- valor novo;
- impacto.

---

# 136. CR manual

A atribuição manual de CR deve ser permitida apenas a utilizadores autorizados.

Deve estar associada, sempre que possível, à ronda ou compensação que a originou.

Quando não exista associação, deve ser emitido alerta.

---

# 137. Eliminar uma atribuição

Eliminar uma atribuição não deve apagar o histórico.

A atribuição deve ser:

- anulada;
- substituída;
- ou marcada como removida.

O valor anterior deve permanecer consultável.

---

# 138. Eliminar dias da escala

A aplicação pode permitir limpar atribuições de determinados dias.

Esta ação deve:

- exigir confirmação;
- indicar quantas células serão afetadas;
- preservar células manuais, salvo escolha expressa;
- criar registo de auditoria;
- permitir identificar o conteúdo removido.

---

# 139. Limpar escala

A funcionalidade de limpar escala deve disponibilizar opções claras.

Exemplos:

- limpar apenas automáticos;
- limpar apenas um intervalo;
- limpar apenas um militar;
- limpar todo o rascunho;
- preservar indisponibilidades;
- preservar DS e DC;
- preservar alterações manuais.

---

# 140. Ações destrutivas

Toda a ação destrutiva deve exigir confirmação.

A confirmação deve indicar concretamente o impacto.

Não deve usar mensagens genéricas como “Tem a certeza?” sem explicar o que será alterado.

---

# 141. Diagnóstico

A aplicação deve possuir um módulo de diagnóstico independente da geração.

O diagnóstico deve poder ser executado:

- após geração;
- após edição;
- antes da validação;
- antes da publicação;
- a pedido do utilizador.

---

# 142. Níveis de diagnóstico

Os resultados devem possuir níveis.

Exemplo:

- erro;
- aviso;
- informação.

---

# 143. Erros de diagnóstico

Um erro representa situação que impede validação ou publicação, salvo decisão normativa expressa.

Exemplos:

- cobertura mínima em falta;
- militar duplicado em serviços incompatíveis;
- serviço atribuído durante BM;
- código inválido;
- militar inativo escalado;
- referência de ciclo ausente.

---

# 144. Avisos de diagnóstico

Um aviso representa situação que exige atenção, mas pode ser autorizada.

Exemplos:

- descanso inferior a oito horas autorizado;
- sequência elevada de dias de trabalho;
- desequilíbrio relevante;
- uso de SEC ou SI por necessidade;
- CR sem associação completa;
- alteração tardia após publicação.

---

# 145. Informações de diagnóstico

Uma informação não representa irregularidade.

Exemplos:

- ausência de PT por falta de sobrantes;
- FF pendentes;
- FC pendentes;
- serviço especial registado;
- versão criada.

---

# 146. Diagnóstico de cobertura

Deve verificar, para cada dia e turno:

- mínimo exigido;
- número atribuído;
- diferença;
- militares atribuídos;
- motivo da falta, quando conhecido.

---

# 147. Diagnóstico de descanso

Deve comparar serviços consecutivos.

Para cada conflito deve indicar:

- militar;
- serviço anterior;
- serviço seguinte;
- hora de fim;
- hora de início;
- descanso calculado;
- mínimo exigido;
- existência de override.

---

# 148. Diagnóstico de ciclo

Deve verificar:

- fase correta;
- continuidade;
- DS;
- DC;
- equipas sem referência;
- alterações manuais sobre folgas;
- incoerências históricas.

---

# 149. Diagnóstico de indisponibilidades

Deve identificar serviços atribuídos durante:

- férias;
- baixa;
- licença;
- diligência;
- tribunal;
- inquérito;
- restrição horária;
- outra indisponibilidade.

---

# 150. Diagnóstico de equidade

Deve apresentar desvios relevantes.

Não deve classificar automaticamente qualquer diferença mínima como erro.

O limiar de alerta deve ser configurável.

---

# 151. Diagnóstico antes da validação

Uma escala não deve passar a validada enquanto existirem erros bloqueantes.

Os avisos devem ser apresentados ao utilizador.

---

# 152. Diagnóstico antes da publicação

Antes da publicação, a aplicação deve voltar a executar os diagnósticos essenciais.

A publicação deve guardar o resultado desse diagnóstico.

---

# 153. Avisos de dia

A aplicação deve permitir associar avisos a uma data.

Exemplos:

- penhora;
- operação;
- evento;
- diligência relevante;
- limitação de viatura;
- necessidade especial.

O aviso não constitui automaticamente um serviço.

---

# 154. Notas

Podem existir notas:

- por dia;
- por militar;
- por atribuição;
- por mês;
- por serviço;
- por versão.

As notas devem ter autoria e data.

---

# 155. Auditoria

A auditoria é obrigatória para todas as alterações relevantes.

---

# 156. Eventos auditáveis

Devem ser auditados, pelo menos:

- criação de militar;
- alteração de militar;
- desativação;
- eliminação autorizada;
- alteração de equipa;
- criação de indisponibilidade;
- edição de indisponibilidade;
- remoção de indisponibilidade;
- geração;
- regeneração;
- edição manual;
- override;
- validação;
- publicação;
- encerramento;
- reabertura;
- criação e alteração de FF;
- criação e alteração de FC;
- exportação;
- backup;
- alteração de configurações.

---

# 157. Conteúdo da auditoria

Cada evento deve conter:

- utilizador;
- data e hora;
- ação;
- entidade;
- identificador;
- valor anterior;
- valor novo;
- motivo;
- origem;
- endereço técnico ou sessão, quando apropriado.

---

# 158. Imutabilidade da auditoria

Os registos de auditoria não devem ser editados ou eliminados através da interface normal.

Qualquer operação extraordinária deve deixar registo externo e administrativo.

---

# 159. Histórico do militar

O histórico deve preservar:

- equipas;
- funções;
- estado ativo;
- restrições;
- serviços;
- indisponibilidades;
- créditos;
- alterações relevantes.

---

# 160. Mudança de equipa

Uma mudança de equipa deve possuir:

- equipa anterior;
- equipa nova;
- data de efeito;
- motivo;
- utilizador.

A mudança não altera retroativamente escalas anteriores.
# 161. Eliminação de militares

A eliminação definitiva de um militar deve ser excecional.

A regra normal é a desativação.

---

# 162. Desativação de militar

Um militar desativado:

- deixa de ser considerado nas gerações futuras;
- mantém todo o histórico;
- permanece nas escalas anteriores;
- mantém créditos e registos associados.

---

# 163. Eliminação definitiva

A eliminação definitiva apenas pode ser permitida quando:

- não existam referências históricas relevantes;
- não existam escalas;
- não existam créditos;
- não existam auditorias dependentes;
- a integridade da base seja preservada.

A operação deve exigir confirmação reforçada.

---

# 164. Dados fictícios

É proibido criar automaticamente:

- militares fictícios;
- equipas fictícias;
- escalas fictícias;
- indisponibilidades fictícias;
- FF fictícias;
- FC fictícias;
- serviços fictícios;
- dados demonstrativos na base real.

---

# 165. Dados iniciais permitidos

Podem ser criados automaticamente apenas elementos estruturais oficiais.

Exemplos:

- códigos de serviço;
- categorias;
- configurações;
- perfil administrativo inicial;
- legenda;
- parâmetros técnicos.

A criação deve ser controlada e documentada.

---

# 166. Importação de dados

A aplicação pode permitir importação.

Antes de confirmar a importação deve:

- validar o formato;
- identificar duplicados;
- apresentar pré-visualização;
- indicar erros;
- permitir cancelar;
- criar backup;
- registar auditoria.

---

# 167. Exportação

A aplicação deve permitir exportar a escala.

Formatos previstos:

- PDF;
- Excel.

Outros formatos podem ser adicionados posteriormente.

---

# 168. Exportação para PDF

O PDF da escala mensal deve ser adequado a impressão em A3.

Deve privilegiar:

- legibilidade;
- identificação clara dos militares;
- dias do mês;
- códigos;
- legenda;
- mês e ano;
- versão;
- estado;
- data de exportação.

---

# 169. Exportação para Excel

A exportação para Excel deve preservar uma estrutura mensal de fácil leitura.

Deve permitir:

- consulta;
- impressão;
- filtragem quando aplicável;
- leitura das siglas;
- identificação da versão;
- identificação da data de exportação.

---

# 170. Fidelidade das exportações

A exportação deve representar a versão selecionada.

Não deve misturar dados de versões diferentes.

Deve indicar se a versão está:

- em rascunho;
- validada;
- publicada;
- encerrada.

---

# 171. Registo das exportações

Cada exportação deve guardar:

- utilizador;
- data e hora;
- tipo;
- mês;
- versão;
- formato;
- nome do ficheiro;
- resultado;
- hash ou identificação técnica, quando aplicável.

---

# 172. Legenda

A aplicação deve apresentar uma legenda das siglas utilizadas.

A legenda deve incluir, pelo menos:

- DS;
- DC;
- FC;
- FF;
- LF;
- LP;
- BM;
- LC;
- LN;
- DCP;
- D24;
- P;
- R;
- CR;
- PT;
- TRIB;
- INQ;
- DIL;
- AT1;
- AT2;
- AT3;
- PO1;
- PO2;
- PO3.

---

# 173. Novos códigos

O Comandante deve poder acrescentar códigos.

Cada código deve indicar:

- sigla;
- designação;
- categoria;
- horário;
- cor;
- prioridade;
- bloqueante ou não;
- compatibilidades;
- estado ativo.

---

# 174. Alteração de códigos

Alterar a designação ou cor de um código não pode destruir o histórico.

A aplicação deve preservar a interpretação aplicável à data, quando necessário.

---

# 175. Cores

As cores devem ser configuráveis.

Por defeito, DS e DC devem ter destaque amarelo, conforme definido.

A escolha de cores deve preservar a legibilidade.

---

# 176. Fonte e apresentação

A interface deve utilizar Segoe UI em todas as páginas, salvo indisponibilidade técnica devidamente tratada.

O uso de texto a negrito deve limitar-se ao essencial.

---

# 177. Interface

A interface deve ser simples, clara e adequada a utilização diária.

Deve evitar:

- excesso de texto;
- excesso de botões;
- excesso de negrito;
- ações escondidas;
- informação fictícia;
- indicadores sem fundamento.

---

# 178. Dashboard

O painel inicial deve apresentar apenas dados reais.

Pode apresentar:

- estado da escala atual;
- faltas de cobertura;
- avisos;
- FF pendentes;
- FC pendentes;
- indisponibilidades próximas;
- serviços por validar;
- ações recentes.

Não deve apresentar números simulados.

---

# 179. Vista mensal

A vista mensal deve permitir visualizar:

- militares em linhas;
- dias em colunas;
- códigos nas células;
- equipas ou secções;
- folgas;
- indisponibilidades;
- avisos;
- alterações manuais;
- conflitos.

---

# 180. Edição da vista mensal

A edição deve ser simples e controlada.

Ao selecionar uma célula, devem estar disponíveis apenas códigos compatíveis ou deve ser apresentado aviso quando se escolha uma exceção.

---

# 181. Preservação visual das alterações manuais

Uma alteração manual deve possuir indicação visual discreta.

O utilizador deve conseguir distinguir:

- atribuição automática;
- atribuição manual;
- atribuição alterada;
- situação com override.

---

# 182. Acesso

A aplicação deve possuir controlo de acessos.

Perfis mínimos:

- Comandante;
- Editor;
- Consulta.

---

# 183. Perfil Comandante

Pode:

- gerir configurações;
- gerir militares;
- gerir equipas;
- gerar;
- editar;
- autorizar overrides;
- validar;
- publicar;
- encerrar;
- reabrir;
- gerir créditos;
- consultar auditoria;
- exportar.

---

# 184. Perfil Editor

Pode executar as ações expressamente autorizadas.

Não deve poder alterar regras estruturais ou autorizar operações críticas sem permissão.

---

# 185. Perfil Consulta

Pode consultar informação autorizada.

Não pode alterar a escala.

---

# 186. Autenticação

As credenciais devem ser protegidas.

As palavras-passe não podem ser guardadas em texto simples.

---

# 187. Aplicação local

A aplicação destina-se prioritariamente a execução local.

O acesso local não elimina a necessidade de:

- autenticação;
- permissões;
- backups;
- auditoria;
- proteção de dados.

---

# 188. Base de dados

A base de dados operacional deve ser preservada.

É proibido usar mecanismos destrutivos como solução normal de atualização.

---

# 189. Migrações

Toda a alteração estrutural à base de dados deve ser efetuada através de migração.

É proibido:

- apagar a base;
- executar `drop_all()` na base real;
- recriar tabelas sem migração;
- perder dados para resolver incompatibilidades.

---

# 190. Backup

Antes de operações de risco deve ser criado backup.

Exemplos:

- migração;
- importação;
- alteração estrutural;
- limpeza ampla;
- recuperação;
- atualização relevante.

---

# 191. Conteúdo do backup

O backup deve incluir, conforme aplicável:

- base de dados;
- configurações;
- ficheiros necessários;
- versão da aplicação;
- data;
- identificação.

---

# 192. Recuperação

A recuperação de backup deve ser documentada.

Não deve ser executada sem confirmação e verificação da integridade do ficheiro.

---

# 193. Logs técnicos

A aplicação deve manter logs técnicos.

Os logs devem registar:

- arranque;
- erros;
- migrações;
- geração;
- exportações;
- falhas;
- eventos técnicos relevantes.

Não devem expor palavras-passe ou dados desnecessários.

---

# 194. Segurança dos dados

A aplicação deve validar todos os dados recebidos.

Deve utilizar:

- validação no servidor;
- proteção CSRF;
- consultas seguras;
- ORM;
- controlo de permissões;
- tratamento de erros.

---

# 195. UTF-8

Todos os ficheiros, dados e exportações devem utilizar codificação compatível com UTF-8.

Devem ser preservados corretamente:

- acentos;
- cedilhas;
- símbolos;
- nomes portugueses;
- designações oficiais.

---

# 196. Testes obrigatórios

A aplicação deve possuir testes automatizados.

Os testes devem utilizar base de dados separada.

Nunca devem utilizar a base real.

---

# 197. Testes do ciclo

Devem validar:

- as seis fases;
- passagem da Fase 6 para a Fase 1;
- continuidade mensal;
- continuidade anual;
- DS;
- DC;
- blocos de um dia;
- blocos de dois dias;
- desfasamento entre equipas.

---

# 198. Testes de cobertura

Devem validar:

- AT1;
- AT2;
- AT3;
- PO1;
- PO2;
- PO3;
- total mínimo diário;
- faltas;
- sobras;
- diagnóstico.

---

# 199. Testes de descanso

Devem validar:

- oito horas exatas;
- menos de oito horas;
- mais de oito horas;
- mudança de dia;
- mudança de mês;
- serviços noturnos;
- override.

---

# 200. Testes de indisponibilidades

Devem validar:

- dia completo;
- intervalo parcial;
- vários dias;
- sobreposição;
- ausência de sobreposição;
- restrição recorrente;
- exceção especial.

---

# 201. Testes de FF

Devem validar:

- aquisição em feriado;
- manutenção do código de serviço no feriado;
- estado pendente;
- agendamento;
- gozo;
- reagendamento;
- cancelamento de agendamento;
- cancelamento do direito;
- transição entre meses;
- saldo.

---

# 202. Testes de FC

Devem validar:

- origem;
- aquisição;
- estado pendente;
- agendamento;
- gozo;
- reagendamento;
- saldo;
- associação à ronda;
- trabalho em folga.

---

# 203. Testes de regeneração

Devem validar:

- preservação de alterações manuais;
- preenchimento de células vazias;
- regeneração apenas automática;
- criação de nova versão;
- ausência de duplicações;
- determinismo.

---

# 204. Testes de auditoria

Devem validar:

- criação de registos;
- valor anterior;
- valor novo;
- utilizador;
- data;
- motivo;
- impossibilidade de alteração normal.

---

# 205. Testes de exportação

Devem validar:

- mês correto;
- versão correta;
- códigos;
- legenda;
- caracteres portugueses;
- estado;
- formato;
- nome do ficheiro.

---

# 206. Testes de regressão

Cada erro corrigido deve originar um teste de regressão.

O teste deve falhar antes da correção e passar depois da correção.

---

# 207. Casos reais

Os testes devem incluir cenários reais ou realisticamente parametrizados do Posto.

Não devem ser inseridos dados pessoais reais nos testes públicos.

Devem ser utilizados identificadores neutros.

---

# 208. Critério de validação

Uma funcionalidade não é considerada concluída apenas porque aparece na interface.

Deve:

- cumprir a regra;
- preservar dados;
- possuir validação;
- possuir teste;
- produzir auditoria quando aplicável;
- tratar erros;
- estar documentada.

---

# 209. Critério de publicação da escala

Uma escala pode ser publicada quando:

- não possui erros bloqueantes;
- foi revista;
- foi validada;
- possui cobertura ou exceções fundamentadas;
- alterações manuais estão identificadas;
- diagnósticos foram executados;
- a versão foi registada.

---

# 210. Critério de encerramento

Uma escala pode ser encerrada quando:

- o período terminou;
- alterações relevantes foram consolidadas;
- FF e FC adquiridas foram registadas;
- serviços executados foram confirmados quando necessário;
- diagnósticos finais foram tratados;
- exportação ou arquivo foi efetuado, quando aplicável.

---

# 211. Alterações às regras

Nenhuma regra deste documento pode ser alterada silenciosamente no código.

Uma alteração normativa deve:

1. ser indicada pelo responsável funcional;
2. ser documentada;
3. atualizar a versão deste ficheiro;
4. avaliar impacto no modelo de dados;
5. avaliar impacto nas escalas existentes;
6. criar migração, quando necessário;
7. criar ou atualizar testes;
8. atualizar o CHANGELOG;
9. atualizar o AI_CONTEXT.

---

# 212. Regras pendentes

Quando uma matéria ainda não esteja suficientemente definida:

- não deve ser inventada uma regra;
- deve ser marcada como pendente;
- o sistema deve permitir configuração ou intervenção manual;
- a implementação automática deve aguardar decisão.

---

# 213. Conflitos entre documentos

Em caso de conflito, a ordem de prevalência é:

1. instrução expressa e atual do responsável funcional;
2. `ESCALA_RULES.md`;
3. `ARCHITECTURE.md`;
4. `CODING_STANDARDS.md`;
5. `DATA_MODEL.md`;
6. `TEST_CASES.md`;
7. `AI_CONTEXT.md`;
8. código existente.

A instrução atual deve posteriormente ser incorporada neste documento.

---

# 214. Responsabilidade do motor

O motor da escala:

- calcula;
- valida;
- sugere;
- atribui dentro das regras;
- explica as decisões.

O motor não decide novas regras operacionais.

---

# 215. Responsabilidade do Comandante

O Comandante mantém a decisão final.

Pode:

- alterar;
- autorizar;
- validar;
- rejeitar;
- publicar;
- justificar exceções.

A aplicação deve apoiar a decisão e preservar o seu registo.

---

# 216. Regra final

A aplicação deve servir as regras operacionais definidas pelo responsável funcional.

A arquitetura deve suportar essas regras.

A base de dados deve preservar essas regras.

Os testes devem comprovar essas regras.

A interface deve tornar essas regras compreensíveis.

O código implementa regras.

O código nunca cria regras.

---

# 217. Controlo de versão do documento

Versão inicial consolidada:

1.0

Alterações futuras devem ser registadas no `CHANGELOG.md`.

Cada alteração deve indicar:

- versão;
- data;
- secções alteradas;
- motivo;
- impacto;
- responsável.

---

# 218. Estado do documento

Este documento constitui a referência normativa principal do projeto Escala de Serviço.

Qualquer implementação incompatível com este documento deve ser considerada incorreta até que:

- o código seja corrigido;
- ou a regra seja formalmente alterada pelo responsável funcional.

---

**Fim do documento — ESCALA_RULES.md**
