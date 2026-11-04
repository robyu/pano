#!/usr/bin/env python3
"""Command-line entry point for the Amcrest console (phase 2).

Starts a LAN-accessible web console for one camera. The camera password is not
accepted on the command line: the browser login screen collects it and the
proxy keeps it in memory only.

By default the server binds 0.0.0.0 and serves routes at the root URL. Use
``--bind 127.0.0.1`` to restrict access to the local machine.
"""

from __future__ import annotations

import argparse
import ipaddress
import logging
import socket
import sys
import webbrowser
from pathlib import Path
from typing import List, Optional

import state
from server import ConsoleServer, local_ip_addresses


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LAN-accessible Amcrest/Dahua camera console (phase 2).",
    )
    parser.add_argument("--camera-ip", required=True, help="camera IPv4/IPv6 address")
    parser.add_argument("--name", help="camera label (default: the IP)")
    parser.add_argument("--user", default="admin", help="username prefill")
    parser.add_argument("--camera-port", type=int, default=80)
    parser.add_argument("--port", type=int, default=8765, help="local console port")
    parser.add_argument(
        "--bind",
        default="0.0.0.0",
        help="console bind address (default: 0.0.0.0; use 127.0.0.1 for local only)",
    )
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        metavar="HOST[:PORT]",
        help="additional Host names accepted by the console (repeatable)",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--request-delay",
        type=float,
        default=None,
        help="seconds between camera requests (default: 1.0 for IP2M-842)",
    )
    parser.add_argument(
        "--auth",
        choices=("auto", "basic", "digest"),
        default="auto",
        help="HTTP auth: auto uses the model, else Basic then Digest challenge",
    )
    parser.add_argument(
        "--model",
        help="camera model, used by --auth auto (e.g. amcrest-ip2m-842)",
    )
    parser.add_argument(
        "--state-dir",
        help="directory for per-camera JSON mirrors and logs (default: amcrest-console/cameras/)",
    )
    parser.add_argument(
        "--state-file",
        help="explicit mirror file for this camera (overrides --state-dir)",
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="print the URL without opening a browser"
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="protocol log verbosity (default: INFO; DEBUG includes payloads)",
    )
    parser.add_argument(
        "--log-file",
        help="override the default <state-dir>/log-<slug>.log path",
    )
    return parser.parse_args(argv)


def setup_logging(level: str, log_file: Path) -> logging.Logger:
    logger = logging.getLogger("amcrest")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler: logging.Handler = logging.FileHandler(
        str(log_file), mode="a", encoding="utf-8"
    )
    try:
        log_file.chmod(0o600)
    except OSError:
        pass
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.handlers[:] = [handler]
    return logger


def default_log_path(
    state_dir: Path, name: Optional[str], host: str
) -> Path:
    """Return the default per-camera log path, ``log-<slug>.log``."""
    return Path(state_dir) / "log-{}.log".format(state.slugify(name or host))


def check_reachable(host: str, port: int, timeout: float) -> Optional[str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return None
    except OSError as error:
        return str(error)


def console_urls(bind_host: str, port: int) -> List[str]:
    if bind_host not in ("0.0.0.0", "::"):
        host = "[{}]".format(bind_host) if ":" in bind_host else bind_host
        return ["http://{}:{}/".format(host, port)]
    urls = []
    ipv6 = bind_host == "::"
    for address in local_ip_addresses():
        if address == "::1" or address.startswith("127."):
            continue
        if (":" in address) != ipv6:
            continue
        host = "[{}]".format(address) if ":" in address else address
        urls.append("http://{}:{}/".format(host, port))
    urls.append("http://127.0.0.1:{}/".format(port))
    return urls


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        camera_ip = str(ipaddress.ip_address(args.camera_ip))
    except ValueError as error:
        print("invalid --camera-ip: {}".format(error), file=sys.stderr)
        return 2

    model = args.model or ""
    request_delay = args.request_delay
    if request_delay is None:
        request_delay = 1.0 if "ip2m" in model.lower() else 0.0

    state_dir = Path(args.state_dir) if args.state_dir else state.DEFAULT_STATE_DIR
    if args.state_file:
        state_path = Path(args.state_file)
    else:
        state_path = state.mirror_path(state_dir, args.name, camera_ip)

    log_path = (
        Path(args.log_file)
        if args.log_file
        else default_log_path(state_dir, args.name, camera_ip)
    )
    logger = setup_logging(args.log_level, log_path)
    logger.info(
        "console starting camera=%s port=%s auth=%s model=%s log_level=%s "
        "log_file=%s",
        camera_ip,
        args.camera_port,
        args.auth,
        args.model or "unknown",
        args.log_level,
        log_path,
    )

    error = check_reachable(camera_ip, args.camera_port, args.timeout)
    if error:
        print(
            "cannot reach camera {}:{}: {}".format(camera_ip, args.camera_port, error),
            file=sys.stderr,
        )
        return 3

    camera_config = {
        "host": camera_ip,
        "port": args.camera_port,
        "auth": args.auth,
        "model": model or None,
        "timeout": args.timeout,
        "request_delay": request_delay,
    }
    try:
        server = ConsoleServer(
            (args.bind, args.port),
            camera_config,
            name=args.name,
            state_path=state_path,
            allow_hosts=args.allow_host,
        )
    except OSError as error:
        print(
            "cannot bind {}:{}: {}".format(args.bind, args.port, error),
            file=sys.stderr,
        )
        return 4

    urls = console_urls(args.bind, server.server_address[1])
    print("Amcrest console for {} ({})".format(args.name or camera_ip, camera_ip))
    print("Listening on {}:{} (login required).".format(args.bind, server.server_address[1]))
    print("Mirror: {}".format(state_path))
    for url in urls:
        print("Open: {}".format(url))
    print("Log: {} ({})".format(log_path, args.log_level.upper()))
    if not args.no_browser:
        webbrowser.open(urls[0])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
