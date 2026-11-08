#!/usr/bin/env python3
"""Parsing, validation, and read-modify-write helpers for camera config.

The camera's CGI interface uses flat ``key=value`` pairs. Phase 3 keeps the
editing surface to the fields declared in :mod:`schemas`; unknown firmware keys
remain visible in the raw viewer but cannot be written.

Everything here is stdlib only and has no camera/network side effects.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List

import schemas


class ConfigError(ValueError):
    """Raised when a section or change set is not safe to apply."""


def canonical(values: Dict[str, str]) -> str:
    return "\n".join(
        "{}={}".format(key, values[key]) for key in sorted(values)
    )


def revision(values: Dict[str, str]) -> str:
    return hashlib.sha256(canonical(values).encode("utf-8")).hexdigest()


def diff_changes(
    name: str, live: Dict[str, str], changes: Dict[str, Any]
) -> Dict[str, str]:
    """Validate changes against the live section and return changed keys."""
    if name not in schemas.SECTIONS:
        raise ConfigError("unknown configuration section: {}".format(name))
    if not isinstance(changes, dict):
        raise ConfigError("changes must be an object")
    normalized: Dict[str, str] = {}
    for key, raw in changes.items():
        if not isinstance(key, str):
            raise ConfigError("config keys must be strings")
        spec = schemas.field_spec(name, key)
        if spec is None or not spec["writable"]:
            raise ConfigError("field is not writable: {}".format(key))
        if key not in live:
            raise ConfigError("field is not present on the camera: {}".format(key))
        try:
            value = schemas.normalize_value(spec, raw)
        except schemas.SchemaError as error:
            raise ConfigError("{}: {}".format(key, error))
        if value is None:
            continue
        if value == live[key]:
            continue
        normalized[key] = value
    return normalized


def apply_changes(
    name: str, live: Dict[str, str], changes: Dict[str, str]
) -> Dict[str, str]:
    merged = dict(live)
    merged.update(changes)
    return merged


def params_for_cgi(changes: Dict[str, str]) -> Dict[str, str]:
    params = {"action": "setConfig"}
    params.update(changes)
    return params


def _path_tokens(name: str, key: str) -> List[Any]:
    if not key.startswith(name):
        raise ConfigError("field does not belong to {}: {}".format(name, key))
    rest = key[len(name):]
    tokens: List[Any] = []
    while rest:
        if rest.startswith("."):
            rest = rest[1:]
            match = re.match(r"[^.\[\]]+", rest)
            if not match:
                raise ConfigError("invalid field path: {}".format(key))
            tokens.append(match.group(0))
            rest = rest[match.end():]
        elif rest.startswith("["):
            match = re.match(r"\[(\d+)\]", rest)
            if not match:
                raise ConfigError("invalid field path: {}".format(key))
            tokens.append(int(match.group(1)))
            rest = rest[match.end():]
        else:
            raise ConfigError("invalid field path: {}".format(key))
    return tokens


def _rpc_value(name: str, key: str, value: str) -> Any:
    spec = schemas.field_spec(name, key)
    if spec is None:
        return value
    if spec["type"] == "boolean":
        return value == "true"
    if spec["type"] == "number":
        return int(value)
    return value


def set_table_value(
    table: Any, name: str, key: str, value: str
) -> None:
    """Set one flat config key in an RPC2 table, preserving other fields."""
    tokens = _path_tokens(name, key)
    if not tokens:
        raise ConfigError("field path is empty: {}".format(key))
    current = table
    for position, token in enumerate(tokens[:-1]):
        next_token = tokens[position + 1]
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                raise ConfigError("RPC2 table is missing path: {}".format(key))
            current = current[token]
        else:
            if not isinstance(current, dict) or token not in current:
                raise ConfigError("RPC2 table is missing path: {}".format(key))
            current = current[token]
        if isinstance(next_token, int) and not isinstance(current, list):
            raise ConfigError("RPC2 table shape mismatch: {}".format(key))
        if isinstance(next_token, str) and not isinstance(current, dict):
            raise ConfigError("RPC2 table shape mismatch: {}".format(key))
    last = tokens[-1]
    if isinstance(last, int):
        if not isinstance(current, list) or last >= len(current):
            raise ConfigError("RPC2 table is missing path: {}".format(key))
        current[last] = _rpc_value(name, key, value)
    else:
        if not isinstance(current, dict) or last not in current:
            raise ConfigError("RPC2 table is missing path: {}".format(key))
        current[last] = _rpc_value(name, key, value)
