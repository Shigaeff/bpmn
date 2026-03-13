---
name: validate-bpmn
description: Validate BPMN 2.0.2 files for XSD schema compliance, semantic correctness, and best practices. Use when checking process definitions, debugging validation errors, or ensuring quality before deployment.
argument-hint: "[arquivo.bpmn] [--skip-schema] [--format json] [--strict]"
allowed-tools: Bash, Read, Grep
---

# BPMN 2.0.2 Validator

Validate BPMN XML files using the `bpmn-validator` CLI tool.

## Your task

Validate the BPMN file(s) specified: `$ARGUMENTS`

### Steps

1. **Run validation** (use `--format json` for structured output):
   ```bash
   bpmn-validator validate $0 --format json --skip-schema
   ```
   If the user passed extra options (`$1`, `$2`, etc.), include them.

2. **Parse the JSON output**:
   - `is_valid`: true/false
   - `summary.errors` / `summary.warnings` / `summary.infos`: counts
   - `issues[]`: array with `rule_id`, `severity`, `message`, `element_id`

3. **Report results**:
   - If valid: confirm success, note any warnings
   - If invalid: list each error with rule ID, element, and message

4. **Suggest fixes** for each error:
   - Read the BPMN file with the Read tool to understand context
   - Explain what the rule expects and how to fix the violation
   - Offer to apply the fix if possible

## CLI reference

```bash
# Validate (semantic only)
bpmn-validator validate arquivo.bpmn --skip-schema

# Validate with XSD schema (requires specs/ downloaded)
bpmn-validator validate arquivo.bpmn

# JSON output
bpmn-validator validate arquivo.bpmn --format json --skip-schema

# Strict mode (warnings also cause exit 1)
bpmn-validator validate arquivo.bpmn --strict --skip-schema

# Exclude specific rules
bpmn-validator validate arquivo.bpmn --exclude-rules PROC-001,BP-001 --skip-schema

# Filter by severity
bpmn-validator validate arquivo.bpmn --severity error --skip-schema

# List all 31 rules
bpmn-validator list-rules

# Download XSD schemas from OMG
bpmn-validator download
```

## Exit codes

- `0` — valid (no errors)
- `1` — invalid (errors found; or warnings in `--strict` mode)
- `2` — configuration error (missing specs, file not found)

## Semantic rules (31 rules)

| Category           | IDs           | Severity | Checks                                   |
|--------------------|---------------|----------|------------------------------------------|
| Process Structure  | PROC-001..005 | ERROR    | Start/end events, reachability           |
| Gateways           | GW-001..004   | ERROR    | Default flow, balanced parallel, event-based |
| Events             | EVT-001..005  | ERROR    | Catch events, boundary events, timers    |
| Tasks              | TASK-001..006 | ERROR    | Message refs, script defs, subprocesses  |
| Sequence Flows     | SF-001..002   | ERROR    | Orphan flows, conditional expressions    |
| Message Flows      | MF-001..002   | ERROR    | Cross-pool constraints                   |
| Collaboration      | COLLAB-001..002 | ERROR  | Pool/participant consistency             |
| Data               | DATA-001..002 | ERROR    | Data object/store references             |
| Best Practices     | BP-001..004   | WARNING/INFO | Naming, empty pools, lanes, docs     |

## Python API (alternative)

```python
from bpmn_validator import BPMNValidator

validator = BPMNValidator(skip_schema=True)
result = validator.validate("arquivo.bpmn")

print(result.is_valid)
for issue in result.errors:
    print(f"[{issue.rule_id}] {issue.element_id}: {issue.message}")
```
