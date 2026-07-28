# Escala de Serviço

Aplicação local Flask para gestão progressiva da Escala de Serviço.

## Versão atual

v1.1 - Regeneração Segura de Atribuições Automáticas AT/PO

Esta versão inclui a infraestrutura inicial, a gestão segura de militares, equipas oficiais A-E, histórico de pertença, referências do ciclo de folgas, restrições individuais, indisponibilidades dos militares, consulta mensal da grelha, edição manual controlada das células, diagnóstico inicial, geração automática AT/PO e regeneração segura de automáticos numa nova versão.

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
/escala/<year>/<month>/versoes/<version_id>/diagnostico
/escala/<year>/<month>/versoes/<version_id>/diagnostico/<run_id>
/escala/<year>/<month>/versoes/<version_id>/gerar
/escala/<year>/<month>/versoes/<version_id>/geracoes
/escala/<year>/<month>/versoes/<version_id>/geracoes/<run_id>
/escala/<year>/<month>/versoes/<version_id>/regenerar
/escala/<year>/<month>/versoes/<version_id>/comparar/<other_version_id>
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

## Estado da v1.1

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
- Diagnóstico central com níveis ERROR, WARNING e INFO.
- Diagnóstico persistido por execução e problema.
- Diagnóstico de cobertura completo para versões com geração concluída.
- Descanso com horários formalizados para AT1-AT3 e PO1-PO3.
- Geração automática inicial de AT1, AT2, AT3, PO1, PO2 e PO3.
- Geração determinística, sem aleatoriedade.
- Execuções persistidas em `generation_runs`.
- Detalhes de elegibilidade, exclusão e seleção persistidos em `assignment_selection_details`.
- Preservação de todas as atribuições manuais.
- Atribuições automáticas criadas com origem SYSTEM.
- CMD excluído de AT/PO.
- SEC e SI usados apenas quando patrulheiros elegíveis não chegam.
- Falta de cobertura registada como aviso/diagnóstico, sem inventar militares.
- Regeneração segura de automáticos AT/PO numa nova versão.
- Versões regeneradas ligadas à versão de origem.
- Comparação consultiva entre versão de origem e versão resultante.
- Células manuais/importadas preservadas na nova versão.
- Automáticos antigos não são copiados.
- Células limpas continuam sem código ativo.
- Sem militares fictícios.
- Sem pertenças de equipa fictícias.
- Sem referências fictícias do ciclo.
- Sem restrições fictícias.
- Sem indisponibilidades fictícias.
- Sem escalas fictícias.
- Sem geração automática de PT.
- Sem criação automática de FF ou FC.
- Sem correção automática de problemas de diagnóstico.
- Sem autenticação completa.
