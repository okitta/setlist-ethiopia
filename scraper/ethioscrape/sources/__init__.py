"""Pluggable data sources. Each exposes a `collect(...)` entry point returning a
`Dataset`, and pure `parse_*` helpers that are unit-testable without a network.
"""
