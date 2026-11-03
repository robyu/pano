#!/usr/bin/env python3
"""Command-line entry point for the Amcrest console (phase 1).

Starts a loopback-only web console for one camera. The camera password is not
accepted on the command line: the browser login screen collects it and the
proxy keeps it in memory only.

Remote use: keep the loopback bind and forward the port over SSH, e.g.
  ssh -L 8765:127.0.0.1:8765 ryu@chuyu-server.local
then browse http://127.0.0.1:8765/s/<token>/
"""

from __future__ import annotations

import argparse
import ipaddress
import secrets
import socket
import sys
import webbrowser
from typing import List, Optional

from server import ConsoleServer


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Loopback-only Amcrest/Dahua camera console (phase 1).",
    )
    parser.add_argument("--camera-ip", required=True, help="camera IPv4/IPv6 address")
    parser.add_argument("--name", help="camera label (default: the IP)")
    parser.add_argument("--user", default="admin", help="username prefill")
    parser.add_argument("--camera-port", type=int, default=80)
    parser.add_argument("--port", type=int, default=8765, help="local console port")
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
        "--no-browser", action="store_true", help="print the URL without opening a browser"
    )
    return parser.parse_args(argv)


def check_reachable(host: str, port: int, timeout: float) -> Optional[str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return None
    except OSError as error:
        return str(error)


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

    error = check_reachable(camera_ip, args.camera_port, args.timeout)
    if error:
        print(
            "cannot reach camera {}:{}: {}".format(camera_ip, args.camera_port, error),
            file=sys.stderr,
        )
        return 3

    token = secrets.token_urlsafe(24)
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
            ("127.0.0.1", args.port), camera_config, token, name=args.name
        )
    except OSError as error:
        print(
            "cannot bind 127.0.0.1:{}: {}".format(args.port, error), file=sys.stderr
        )
        return 4

    url = "http://127.0.0.1:{}/s/{}/".format(server.server_address[1], token)
    print("Amcrest console for {} ({})".format(args.name or camera_ip, camera_ip))
    print("Listening on 127.0.0.1 only.")
    print("Open: {}".format(url))
    print(
        "Remote: ssh -L {port}:127.0.0.1:{port} ryu@chuyu-server.local".format(
            port=server.server_address[1]
        )
    )
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
