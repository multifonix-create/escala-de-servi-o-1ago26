# Escala de Serviço

Aplicação local Flask para gestão progressiva da Escala de Serviço.

## Versão atual

v0.3 - Gestão de Equipas e Histórico de Pertença

Esta versão inclui a infraestrutura inicial, a gestão segura de militares do efetivo e a gestão das equipas oficiais A-E com histórico de pertença.

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
/militares/<id>/equipa
/militares/<id>/equipa/mudar
/militares/<id>/historico-equipas
```

## Testes

```powershell
pytest
```

## Estado da v0.3

- Equipas oficiais A-E criadas como dados estruturais.
- Sem militares fictícios.
- Sem pertenças de equipa fictícias.
- Sem escalas.
- Sem motor de geração.
- Sem ciclo de folgas.
- Sem autenticação completa.
