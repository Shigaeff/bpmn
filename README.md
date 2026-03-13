# BPMN 2.0.2 Validator

Validador de arquivos BPMN 2.0.2 com validacao XSD (schema) e 31 regras semanticas extraidas da especificacao OMG.

## Recursos

- **Validacao XSD** contra a especificacao oficial BPMN 2.0.2
- **31 regras semanticas** em 9 categorias (estrutura, gateways, eventos, tarefas, fluxos, mensagens, colaboracao, dados, boas praticas)
- **CLI** com saida texto e JSON, filtragem por severidade
- **Biblioteca Python** com API publica tipada (PEP 561)
- **Seguranca**: protecao contra XXE, XML bombs e arquivos excessivamente grandes (limite 50 MB)

## Instalacao

```bash
pip install -e .
```

Para desenvolvimento:

```bash
pip install -e ".[dev]"
```

## Uso via CLI

### Baixar schemas XSD

```bash
bpmn-validator download
bpmn-validator download --specs-dir ./my-specs
bpmn-validator download --force  # re-baixar mesmo se ja existem
```

### Validar arquivos BPMN

```bash
# Validacao completa (XSD + semantica)
bpmn-validator validate processo.bpmn

# Apenas validacao semantica (sem XSD)
bpmn-validator validate processo.bpmn --skip-schema

# Saida JSON
bpmn-validator validate processo.bpmn --format json

# Filtrar por severidade
bpmn-validator validate processo.bpmn --severity error

# Excluir regras especificas
bpmn-validator validate processo.bpmn --exclude-rules PROC-001,BP-001

# Modo estrito (warnings tambem causam exit code 1)
bpmn-validator validate processo.bpmn --strict

# Validar multiplos arquivos
bpmn-validator validate *.bpmn --format json
```

### Listar regras disponiveis

```bash
bpmn-validator list-rules
```

## Uso como biblioteca Python

```python
from bpmn_validator import BPMNValidator

validator = BPMNValidator(skip_schema=True)
result = validator.validate("processo.bpmn")

print(result.is_valid)        # True/False
print(result.to_json())       # JSON estruturado
print(result.to_text())       # Texto legivel

for issue in result.errors:
    print(f"[{issue.rule_id}] {issue.element_id}: {issue.message}")
```

## Regras semanticas (31 regras)

| Categoria | IDs | Severidade | Descricao |
|-----------|-----|------------|-----------|
| Process Structure | PROC-001..005 | ERROR | Start/end events obrigatorios, elementos alcancaveis |
| Gateways | GW-001..004 | ERROR | Default flow, balanceamento parallel, event-based |
| Events | EVT-001..005 | ERROR | Catch events, boundary events, timers |
| Tasks | TASK-001..006 | ERROR | Message refs, script defs, subprocessos |
| Sequence Flows | SF-001..002 | ERROR | Fluxos orfaos, expressoes condicionais |
| Message Flows | MF-001..002 | ERROR | Fluxos entre pools diferentes |
| Collaboration | COLLAB-001..002 | ERROR | Pools e participantes |
| Data | DATA-001..002 | ERROR | Referencias a data objects/stores |
| Best Practices | BP-001..004 | WARNING/INFO | Nomes, pools vazios, lanes, documentacao |

## Seguranca

- **XXE protection**: parser lxml com `resolve_entities=False`, `no_network=True`, `huge_tree=False`
- **XML bombs**: mitigacao via bloqueio de resolucao de entidades
- **Limite de tamanho**: arquivos > 50 MB sao rejeitados
- **Tratamento seguro**: arquivos ausentes, vazios, binarios e malformados

## Testes

```bash
# Suite completa com coverage
python -m pytest tests/ -v --cov=bpmn_validator --cov-fail-under=100

# Linting e type check
ruff check bpmn_validator/ tests/
ruff format --check bpmn_validator/ tests/
mypy bpmn_validator/ --strict
```

207 testes com 100% de cobertura de codigo.

## Estrutura do projeto

```
bpmn_validator/           # Biblioteca core
  __init__.py             # Exports publicos + __version__
  models.py               # Severity, ValidationIssue, ValidationResult
  parser.py               # Parser BPMN XML -> modelo interno
  schema_validator.py     # Validacao XSD via lxml
  semantic_validator.py   # Orquestrador de regras
  validator.py            # Fachada principal (BPMNValidator)
  spec_downloader.py      # Download dos schemas XSD
  py.typed                # PEP 561 marker
  rules/                  # 31 regras semanticas modulares
tests/                    # 207 testes (100% coverage)
specs/                    # XSDs baixados (gitignored)
```

## Licenca

MIT
