# Afinacao Operacional v1.9

Este documento regista conclusoes de teste operacional e afinacoes propostas ao gerador.

Nao devem ser registados nomes, NIM ou outros dados pessoais reais neste documento. Quando necessario, usar referencias anonimizadas.

## Estado Inicial

Na implementacao v1.9 nao foram importados dados reais e nao foi executada geracao operacional real.

Assim, nao houve alteracao de regras, pesos ou prioridades do gerador AT/PO/PT.

## Formato de Registo

Cada observacao futura deve seguir este formato:

```text
Data:
Mes testado:
Versao de teste:
Sintoma observado:
Regra oficial relacionada:
Impacto operacional:
Dados anonimizados:
Decisao do Comandante:
Alteracao proposta:
Estado:
```

## Limites

A afinacao nao pode:

* alterar o ciclo oficial sem instrucao explicita;
* ignorar descanso minimo;
* remover preservacao de alteracoes manuais;
* criar militares, equipas ou escalas ficticias;
* gerar Ronda, CR ou remunerados automaticamente nesta fase;
* transformar um teste operacional em versao oficial.

## Pendencias

* Executar importacao real apenas apos CSV validado.
* Comparar teste operacional com escala real fornecida pelo utilizador, se existir.
* Identificar falhas recorrentes de cobertura, equidade ou exclusao.
* Propor ajustes pequenos e documentados antes de qualquer alteracao ao motor.
