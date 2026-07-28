# Guia de Teste Operacional v1.9

Este guia descreve o fluxo local para testar a aplicacao com dados reais fornecidos pelo utilizador.

## 1. Preparar dados

1. Preencher um CSV com o cabecalho esperado indicado abaixo.
2. Usar apenas dados reais autorizados.
3. Nao inserir linhas de exemplo, nomes ficticios ou equipas ficticias.

Campos esperados:

```text
nim,nome,sobrenome,tipo_funcional,equipa,contacto,voluntario_remunerados,ativo,data_inicio,data_fim,apto_cr,notas
```

O contacto aceita formato nacional ou `+351` e é normalizado antes de gravar. O campo `voluntario_remunerados` é informativo nesta fase e não altera o motor da escala.

## 2. Pre-visualizar importacao

```powershell
$env:FLASK_APP = "run.py"
flask preview-military-import caminho\para\militares.csv
```

A pre-visualizacao deve indicar total de linhas, validas, invalidas, duplicados, existentes, bloqueios e avisos.

## 3. Importar dados reais

Executar apenas quando a pre-visualizacao estiver sem bloqueios:

```powershell
$env:FLASK_APP = "run.py"
flask import-military-data caminho\para\militares.csv --confirm
```

A aplicacao cria backup automatico antes de escrever. Se o backup falhar, a importacao deve ser abortada.

## 4. Validar prontidao

```powershell
flask validate-real-data
```

Tambem pode ser usada a pagina:

```text
http://127.0.0.1:5001/controlo-operacional
```

Estados possiveis:

* `Nao preparado`;
* `Preparado com avisos`;
* `Preparado para gerar`.

## 5. Conferir ciclo

Usar `/controlo-operacional/ciclo` para confirmar, por equipa e intervalo, a fase calculada e os codigos `DS`/`DC`.

Esta consulta e read-only.

## 6. Criar teste operacional

Usar `/controlo-operacional/teste/criar`.

A versao criada fica marcada como:

```text
TESTE OPERACIONAL - NAO PUBLICAR
```

Esta versao nao pode ser publicada.

## 7. Gerar, diagnosticar e exportar

Se os dados estiverem preparados, usar as rotas normais da escala para gerar, diagnosticar e exportar.

Excel e PDF de teste operacional devem conter o selo e nomes com `Teste_Operacional`.

## 8. Avaliar ou arquivar

Usar `/controlo-operacional` para avaliar ou arquivar o teste.

Decisoes de avaliacao:

* `REJECTED`;
* `ACCEPTABLE_WITH_CHANGES`;
* `APPROVED_REFERENCE`.

Arquivar um teste nao equivale a encerrar uma escala oficial.
