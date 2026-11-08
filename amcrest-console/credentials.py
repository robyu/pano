#!/usr/bin/env python3
"""Non-interactive credential lookup shared by the discovery tool and console.

The console normally asks for the camera password in the browser login screen
and keeps it in memory only. The tools that run without a UI still need a
password, so this module implements the documented precedence:

1. ``--pano-config`` — look the camera up by IP in a pano JSON config and use
   the credentials embedded in its ``admin_url`` / ``live_url``.
2. ``$AMCREST_PASSWORD`` (or whatever ``--password-env`` names).
3. An interactive :func:`getpass.getpass` prompt, but only when stdin is a tty.

There is deliberately no ``--password`` flag: a command-line password would
leak into the shell history and the process table. Passwords returned here are
handed straight to :class:`camera.CameraClient` and never logged or stored.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from camera import CameraError


def load_pano_camera(
    path: Path, camera_ip: str, name: Optional[str]
) -> Dict[str, str]:
    """Return name/user/password/model for one camera in a pano JSON config."""
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    candidates: List[Dict[str, Any]] = []
    for key, value in config.items():
        if key.startswith("@"):
            continue
        if key.endswith("camera_list") and isinstance(value, list):
            for camera in value:
                if isinstance(camera, dict):
                    candidates.append(camera)
    for camera in candidates:
        if name and camera.get("name") != name:
            continue
        for key in ("admin_url", "live_url"):
            url = camera.get(key) or ""
            try:
                host = urllib.parse.urlsplit(url).hostname
            except ValueError:
                host = None
            if host == camera_ip:
                parsed = urllib.parse.urlsplit(url)
                if parsed.username and parsed.password:
                    return {
                        "name": str(camera.get("name") or name or camera_ip),
                        "user": urllib.parse.unquote(parsed.username),
                        "password": urllib.parse.unquote(parsed.password),
                        "model": str(camera.get("model") or ""),
                    }
    raise CameraError(
        "no camera with credentials found for ip {} in {}".format(camera_ip, path)
    )


def resolve_credentials(args: argparse.Namespace) -> Tuple[str, str, str, str]:
    """Return ``(name, user, password, model)`` for ``args.ip``.

    Raises :class:`camera.CameraError` when no password is available and stdin
    is not a terminal, so batch callers fail fast instead of hanging.
    """
    name = args.name or args.ip
    model = getattr(args, "model", None) or ""
    if args.pano_config:
        camera = load_pano_camera(Path(args.pano_config), args.ip, args.name)
        return (
            camera["name"],
            args.user or camera["user"],
            camera["password"],
            model or camera.get("model", ""),
        )
    password = os.environ.get(args.password_env)
    if password:
        return name, args.user, password, model
    if sys.stdin.isatty():
        password = getpass.getpass(
            "Password for {}@{}: ".format(args.user, args.ip)
        )
        return name, args.user, password, model
    raise CameraError(
        "no password: set ${} or pass --pano-config".format(args.password_env)
    )
