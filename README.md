# Escala de Serviço

Aplicação local Flask para gestão progressiva da Escala de Serviço.

## Versão atual

v0.8 - Edição Manual e Preservação de Alterações

Esta versão inclui a infraestrutura inicial, a gestão segura de militares, equipas oficiais A-E, histórico de pertença, referências do ciclo de folgas, restrições individuais, indisponibilidades dos militares, consulta mensal da grelha e edição manual controlada das células.

## Requisitos

- Python 3.11 ou superior
- SQLite

## Instalar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Inicializar migracoes

```powershell
$env:FLASK_APP = "run.py"
flask db init
```

Este comando só é necessário quando a pasta `migrations/` ainda não existe.

## Aplicar migrações

```powershell
$env:FLASK_APP = "run.py"
flask db upgrade
```

## Iniciar

```powershell
$env:FLASK_APP = "run.py"
flask run --host 127.0.0.1 --port 5000
```

Tambem pode ser executada com:

```powershell
python run.py
```

A aplicação fica disponível em:

```text
http://127.0.0.1:5000/
```

Rotas principais:

```text
/
/health
/militares
/militares/novo
/equipas
/ciclo
/ciclo/configurar
/ciclo/pre-visualizar
/restricoes
/indisponibilidades
/escala
/escala/<year>/<month>
/escala/<year>/<month>/versoes
/escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>
/escala/<year>/<month>/versoes/<version_id>/militares/<military_id>/dias/<date>/historico
/equipas/<id>/ciclo
/equipas/<id>/ciclo/nova-referencia
/equipas/<id>/ciclo/historico
/militares/<id>/equipa
/militares/<id>/equipa/mudar
/militares/<id>/historico-equipas
/militares/<id>/restricoes
/militares/<id>/restricoes/nova
/militares/<id>/restricoes/testar
/militares/<id>/indisponibilidades
/militares/<id>/indisponibilidades/nova
/militares/<id>/indisponibilidades/testar
```

## Testes

```powershell
pytest
```

## Estado da v0.8

- Equipas oficiais A-E criadas como dados estruturais.
- Referências do ciclo configuráveis manualmente por equipa.
- Cálculo determinístico de fases, DS e DC.
- Restrições individuais configuráveis por militar.
- Tipos de restrição suportados: indisponível, disponível apenas e disponibilidade especial.
- Avaliador central de compatibilidade com datas, dias da semana e janelas horárias.
- Indisponibilidades concretas configuráveis por militar.
- Códigos suportados: LF, LP, BM, LC, LN, DIL, TRIB, INQ, FORMACAO, TIRO e OUTRA.
- Estados suportados: PLANNED, CONFIRMED e CANCELLED.
- Compensação em DS/DC apenas registada, sem criação automática de FF ou FC.
- Meses de escala criáveis manualmente em estado DRAFT.
- Versão inicial criada por mês com origem INITIAL.
- Grelha mensal calculada dinamicamente a partir de militares, histórico de equipas, ciclo, restrições e indisponibilidades.
- Edição manual de células em versões DRAFT.
- Atribuições manuais persistidas com origem MANUAL.
- Histórico de alterações por célula.
- Bloqueio, desbloqueio, limpeza lógica e override explícito.
- Sem militares fictícios.
- Sem pertenças de equipa fictícias.
- Sem referências fictícias do ciclo.
- Sem restrições fictícias.
- Sem indisponibilidades fictícias.
- Sem escalas fictícias.
- Sem motor de geração.
- Sem geração automática de AT/PO/PT.
- Sem criação automática de FF ou FC.
- Sem autenticação completa.
