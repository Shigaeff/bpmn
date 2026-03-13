# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-12

### Added

- BPMN 2.0.2 XML parser with full namespace support
- XSD schema validation against the official BPMN 2.0.2 specification
- 31 semantic validation rules across 9 categories:
  - **Process structure** (PROC-001 to PROC-005): start/end events, reachability
  - **Gateways** (GW-001 to GW-004): default flows, balanced parallel gateways, conditions
  - **Events** (EVT-001 to EVT-005): boundary events, compensation, signals, timers
  - **Tasks** (TASK-001 to TASK-006): service/script tasks, multi-instance, loop config
  - **Sequence flows** (SF-001 to SF-002): orphan flows, conditional flow expressions
  - **Message flows** (MF-001 to MF-002): cross-pool constraints
  - **Collaboration** (COLLAB-001 to COLLAB-002): pool-process mapping, valid endpoints
  - **Data** (DATA-001 to DATA-002): association targets, data object references
  - **Best practices** (BP-001 to BP-004): naming, empty pools, lane usage, documentation
- CLI with JSON and text output, configurable severity filtering
- Automatic BPMN 2.0.2 XSD spec download and caching

### Security

- XXE protection: all XML parsing uses a hardened `lxml` parser with `resolve_entities=False`, `no_network=True`, and `huge_tree=False`
- XML bomb (billion laughs) mitigation via entity resolution blocking
- File size limit (50 MB) to prevent denial-of-service via oversized inputs

### Reliability

- Graceful error handling for missing, empty, binary, and malformed files
- Friendly error messages for corrupted XSD schemas
- Network timeout (30s) for spec downloads with atomic temp-file handling
- Safe attribute access across all rule implementations
- Full mypy strict compliance (0 errors across 19 source files)
- 207 tests with 100% code coverage
