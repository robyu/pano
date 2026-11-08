#!/usr/bin/env python3
"""Command-line entry point for the Amcrest console.

Default mode starts a LAN-accessible web console for one camera. The camera
password is not accepted on the command line: the browser login screen collects
it and the proxy keeps it in memory only. By default the server binds 0.0.0.0
and serves routes at the root URL; use ``--bind 127.0.0.1`` to restrict access
to the local machine.

``--noui --config {read,write}`` is the scriptable mode: it never binds a port
and never opens a browser. ``read`` dumps every allowlisted section to a JSON
file for offline editing; ``write`` pushes that file back -- except for the
``Network`` section, which must match the camera exactly or the run aborts
before any write, because network changes have to be made interactively.
"""

from __future__ import annotations

import argparse
import ipaddress
import logging
import socket
import sys
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

import configfile
import credentials
import state
from camera import AuthError, CameraClient, CameraError
from server import ConsoleServer, local_ip_addresses

EXIT_OK = 0
EXIT_UNREACHABLE = 3
EXIT_BIND = 4
EXIT_CREDENTIALS = 5
EXIT_CONFIG_FILE = 6
EXIT_NETWORK_DIFF = 7
EXIT_WRITE = 8

DEFAULT_BIND = "0.0.0.0"
DEFAULT_PORT = 8765


EPILOG = """\
examples:

  1. interactive web console (default): binds 0.0.0.0:8765, prints LAN URLs,
     and opens a browser. Credentials are entered in the browser login screen.
       python3 console.py --ip 192.168.2.121 --name cam-01

  2. non-interactive config read: dump every allowlisted section to
     cameras/config-cam-01.json for offline editing. No port is bound.
       AMCREST_PASSWORD=... python3 console.py --ip 192.168.2.121 \\
         --name cam-01 --noui --config read

  3. non-interactive config write: apply an edited file back to the camera.
     The file's Network section must match the camera exactly.
       AMCREST_PASSWORD=... python3 console.py --ip 192.168.2.121 \\
         --name cam-01 --noui --config write \\
         --config-file cameras/config-cam-01.json

     preview the same run without writing anything:
       python3 console.py --ip 192.168.2.121 --name cam-01 \\
         --noui --config write --dry-run

credentials for --noui: --pano-config, then $AMCREST_PASSWORD (see
--password-env), then an interactive prompt when stdin is a terminal.
There is no --password flag.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LAN-accessible Amcrest/Dahua camera console.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ip", required=True, help="camera IPv4/IPv6 address")
    parser.add_argument("--name", help="camera label (default: the IP)")
    parser.add_argument("--user", default="admin", help="username prefill")
    parser.add_argument("--camera-port", type=int, default=80)
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="local console port"
    )
    parser.add_argument(
        "--bind",
        default=DEFAULT_BIND,
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
        help="seconds between camera requests (default: 1.0, or 0 when --model is a non-IP2M camera)",
    )
    parser.add_argument(
        "--auth",
        choices=("auto", "basic", "digest"),
        default="auto",
        help="HTTP auth: auto uses a supplied/detected model, else Basic then Digest challenge",
    )
    parser.add_argument(
        "--model",
        help="optional model override; otherwise detected from the camera at login",
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
        "--backup-dir",
        help="directory for pre-write configuration backups (default: amcrest-console/backups/)",
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
    parser.add_argument(
        "--noui",
        action="store_true",
        help="run without the web console: perform one --config action and exit",
    )
    parser.add_argument(
        "--config",
        choices=("read", "write"),
        default=None,
        help=(
            "non-interactive configuration action; requires --noui "
            "(read: camera -> file; write: file -> camera)"
        ),
    )
    parser.add_argument(
        "--config-file",
        help=(
            "configuration file for --config (default: "
            "<state-dir>/config-<slug>.json)"
        ),
    )
    parser.add_argument(
        "--pano-config",
        help="read credentials for --ip from a pano JSON config",
    )
    parser.add_argument(
        "--password-env",
        default="AMCREST_PASSWORD",
        help="environment variable holding the camera password (default: AMCREST_PASSWORD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="with --config write: print the planned changes without writing",
    )
    parser.add_argument(
        "--include-secrets",
        action="store_true",
        help=(
            "with --config read: store secret values (for example the NAS/FTP "
            "password) instead of <redacted> (the file stays mode 0600)"
        ),
    )
    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Enforce the --noui contract; parser.error exits with status 2."""
    if args.noui and args.config is None:
        parser.error("--noui requires --config {read,write}")
    if args.config and not args.noui:
        parser.error("--config requires --noui")
    if not args.noui:
        return
    if args.port != DEFAULT_PORT:
        parser.error("--port has no effect with --noui")
    if args.bind != DEFAULT_BIND:
        parser.error("--bind has no effect with --noui")
    if args.allow_host:
        parser.error("--allow-host has no effect with --noui")
    if args.no_browser:
        parser.error("--no-browser has no effect with --noui")
    if args.dry_run and args.config != "write":
        parser.error("--dry-run requires --config write")
    if args.include_secrets and args.config != "read":
        parser.error("--include-secrets requires --config read")


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


def camera_meta(
    camera_config: Dict[str, Any],
    name: str,
    state_path: Optional[Path],
    client: Optional[CameraClient] = None,
) -> Dict[str, Any]:
    """Mirror/backup metadata, reusing the model and firmware already known."""
    mirror = state.load(state_path) if state_path else None
    previous = (mirror or {}).get("camera") or {}
    model = camera_config.get("model") or previous.get("model")
    firmware = previous.get("firmware")
    if client is not None and (not model or not firmware):
        try:
            identity = client.identity()
            magic = identity.get("magic") or {}
            device = magic.get("getDeviceType") or {}
            software = magic.get("getSoftwareVersion") or {}
            model = model or (
                device.get("type")
                or device.get("deviceType")
                or device.get("DeviceType")
            )
            firmware = firmware or software.get("version")
        except CameraError:
            pass
    return {
        "name": name,
        "host": camera_config.get("host"),
        "port": int(camera_config.get("port", 80)),
        "model": model,
        "firmware": firmware,
    }


def save_mirror(
    state_path: Path,
    meta: Dict[str, Any],
    configuration: Dict[str, Any],
    verified: bool = True,
    stale: bool = False,
    last_apply: Optional[str] = None,
) -> None:
    doc = state.new_mirror(
        meta,
        configuration,
        stale=stale,
        verified=verified,
        last_apply=last_apply,
    )
    state.save(state_path, doc)


def mirror_configuration(state_path: Optional[Path]) -> Dict[str, Any]:
    if not state_path:
        return {}
    mirror = state.load(state_path)
    return (mirror or {}).get("configuration") or {}


def batch_config_read(
    client: CameraClient,
    meta: Dict[str, Any],
    config_path: Path,
    state_path: Optional[Path],
    include_secrets: bool,
) -> int:
    sections, errors = configfile.read_sections(
        client, include_secrets=include_secrets
    )
    doc = state.new_backup(
        meta, sections, complete=not errors, stale=bool(errors)
    )
    if errors:
        doc["errors"] = errors
    try:
        state.save(
            config_path, doc, sanitize_values=not include_secrets
        )
    except OSError as error:
        print(
            "cannot write configuration file {}: {}".format(config_path, error),
            file=sys.stderr,
        )
        return EXIT_CONFIG_FILE

    if state_path:
        configuration = {
            configfile.configuration_key(name): payload
            for name, payload in sections.items()
        }
        save_mirror(state_path, meta, configuration)

    keys = sum(
        len(payload.get("values") or {}) for payload in sections.values()
    )
    print("Camera: {} ({})".format(meta.get("name"), meta.get("host")))
    if meta.get("model"):
        print("Model: {}  Firmware: {}".format(
            meta.get("model"), meta.get("firmware") or "(unknown)"
        ))
    print("Config file: {}".format(config_path))
    print(
        "Sections: {} ({} keys)".format(
            ", ".join(configfile.ordered_sections(sections)) or "(none)", keys
        )
    )
    if include_secrets:
        print("Secrets: included (file mode 0600)")
    else:
        print("Secrets: redacted (use --include-secrets to export them)")
    if state_path:
        print("Mirror: {}".format(state_path))
    for item in errors:
        print("Warning: {}: {}".format(item["section"], item["error"]))
    return EXIT_OK


def batch_config_write(
    client: CameraClient,
    meta: Dict[str, Any],
    config_path: Path,
    state_path: Optional[Path],
    backup_dir: Path,
    dry_run: bool,
) -> int:
    try:
        doc = configfile.load_document(config_path)
    except configfile.ConfigFileError as error:
        print(str(error), file=sys.stderr)
        return EXIT_CONFIG_FILE

    sections = doc.get("sections") or {}
    file_network = sections.get(configfile.NETWORK_SECTION)
    if not isinstance(file_network, dict):
        print(
            "{}: no Network section; the camera's network settings cannot be "
            "compared, so nothing was written".format(config_path),
            file=sys.stderr,
        )
        return EXIT_CONFIG_FILE

    try:
        live_network = client.get_section(configfile.NETWORK_SECTION)
    except CameraError as error:
        print(
            "cannot read the camera's Network section: {}".format(error),
            file=sys.stderr,
        )
        return EXIT_WRITE

    mismatches = configfile.network_mismatches(
        live_network["values"], file_network.get("values") or {}
    )
    if mismatches:
        print(
            "The camera's Network settings differ from {}.".format(config_path),
            file=sys.stderr,
        )
        print(configfile.format_mismatches(mismatches), file=sys.stderr)
        print(
            "Network changes must be made interactively: run the console "
            "without --noui and use the Configuration tab.",
            file=sys.stderr,
        )
        return EXIT_NETWORK_DIFF

    print("Camera: {} ({})".format(meta.get("name"), meta.get("host")))
    print("Config file: {}".format(config_path))
    print(
        "Network: matches the camera ({} keys)".format(
            len(live_network["values"])
        )
    )

    plans, plan_errors = configfile.plan_writes(client, doc)
    for item in plan_errors:
        print("Error: {}: {}".format(item["section"], item["error"]), file=sys.stderr)

    if dry_run:
        pending = [plan for plan in plans if plan["changes"]]
        if not pending:
            print("Dry run: no changes; the camera already matches the file.")
        else:
            print("Dry run: {} section(s) would change.".format(len(pending)))
            for plan in pending:
                print(
                    "  {}: {}".format(
                        plan["name"], ", ".join(sorted(plan["changes"]))
                    )
                )
        print("Dry run: no writes were sent to the camera.")
        return EXIT_OK if not plan_errors else EXIT_WRITE

    try:
        backup_path, _backup = configfile.write_backup(
            client,
            meta,
            backup_dir,
            str(meta.get("name")),
            str(meta.get("host") or ""),
        )
    except CameraError as error:
        print("cannot create a pre-write backup: {}".format(error), file=sys.stderr)
        return EXIT_WRITE
    print("Backup: {}".format(backup_path))

    report = configfile.apply_document(client, doc, backup_path=backup_path)
    for item in report["errors"]:
        print("Error: {}: {}".format(item["section"], item["error"]), file=sys.stderr)

    configuration = mirror_configuration(state_path)
    for result in report["results"]:
        name = result["name"]
        values = result.get("values") or {}
        configuration[configfile.configuration_key(name)] = (
            configfile.section_payload(
                name,
                values,
                duplicates=result.get("duplicates"),
                stale=not result["verified"],
            )
        )
        if result["changed"] and result["verified"]:
            print(
                "{}: applied {} key(s): {}".format(
                    name,
                    len(result.get("keys") or []),
                    ", ".join(sorted(result.get("keys") or [])),
                )
            )
        elif result.get("error"):
            print("{}: failed: {}".format(name, result["error"]))
        elif result.get("mismatches"):
            print(
                "{}: verification failed:\n{}".format(
                    name, configfile.format_mismatches(result["mismatches"])
                )
            )
        else:
            print("{}: unchanged".format(name))

    if state_path:
        save_mirror(
            state_path,
            meta,
            configuration,
            verified=report["verified"],
            stale=bool(report["errors"]),
            last_apply=state.now_iso(),
        )
        print("Mirror: {}".format(state_path))

    changed = configfile.changed_results(report["results"])
    print(
        "Sections changed: {} of {}".format(
            len(changed), len(report["results"])
        )
    )
    if report["errors"]:
        return EXIT_WRITE
    if not report["changed"]:
        print("The camera already matches the configuration file.")
    return EXIT_OK


def run_batch(
    args: argparse.Namespace,
    camera_ip: str,
    camera_config: Dict[str, Any],
    name: str,
    state_path: Optional[Path],
    backup_dir: Path,
    config_path: Path,
    logger: logging.Logger,
) -> int:
    try:
        _name, user, password, model = credentials.resolve_credentials(args)
    except CameraError as error:
        print("cannot resolve credentials: {}".format(error), file=sys.stderr)
        return EXIT_CREDENTIALS
    if model and not camera_config.get("model"):
        camera_config["model"] = model

    client = CameraClient(
        camera_config["host"],
        int(camera_config.get("port", 80)),
        user,
        password,
        timeout=float(camera_config.get("timeout", 20.0)),
        auth=str(camera_config.get("auth", "auto")),
        model=camera_config.get("model") or None,
        request_delay=float(camera_config.get("request_delay", 0.0)),
        logger=logging.getLogger("amcrest.camera"),
    )
    try:
        client.verify_credentials()
    except AuthError as error:
        print("authentication error: {}".format(error), file=sys.stderr)
        return EXIT_CREDENTIALS
    except CameraError as error:
        print("camera error: {}".format(error), file=sys.stderr)
        return EXIT_UNREACHABLE
    detected = client.detect_model()
    if detected and not camera_config.get("model"):
        camera_config["model"] = detected

    meta = camera_meta(camera_config, name, state_path, client)
    logger.info(
        "batch mode config=%s file=%s camera=%s model=%s",
        args.config,
        config_path,
        camera_ip,
        meta.get("model") or "unknown",
    )
    if args.config == "read":
        return batch_config_read(
            client, meta, config_path, state_path, args.include_secrets
        )
    return batch_config_write(
        client, meta, config_path, state_path, backup_dir, args.dry_run
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)
    try:
        camera_ip = str(ipaddress.ip_address(args.ip))
    except ValueError as error:
        print("invalid --ip: {}".format(error), file=sys.stderr)
        return 2

    model = args.model or ""
    request_delay = args.request_delay
    if request_delay is None:
        request_delay = (
            0.0 if model and "ip2m" not in model.lower() else 1.0
        )

    state_dir = Path(args.state_dir) if args.state_dir else state.DEFAULT_STATE_DIR
    if args.state_file:
        state_path = Path(args.state_file)
    else:
        state_path = state.mirror_path(state_dir, args.name, camera_ip)
    backup_dir = Path(args.backup_dir) if args.backup_dir else state.DEFAULT_BACKUP_DIR
    config_path = (
        Path(args.config_file)
        if args.config_file
        else configfile.document_path(state_dir, args.name, camera_ip)
    )

    log_path = (
        Path(args.log_file)
        if args.log_file
        else default_log_path(state_dir, args.name, camera_ip)
    )
    logger = setup_logging(args.log_level, log_path)
    logger.info(
        "console starting camera=%s port=%s auth=%s model=%s log_level=%s "
        "log_file=%s noui=%s config=%s",
        camera_ip,
        args.camera_port,
        args.auth,
        args.model or "unknown",
        args.log_level,
        log_path,
        args.noui,
        args.config or "-",
    )

    error = check_reachable(camera_ip, args.camera_port, args.timeout)
    if error:
        print(
            "cannot reach camera {}:{}: {}".format(camera_ip, args.camera_port, error),
            file=sys.stderr,
        )
        return EXIT_UNREACHABLE

    camera_config = {
        "host": camera_ip,
        "port": args.camera_port,
        "auth": args.auth,
        "model": model or None,
        "timeout": args.timeout,
        "request_delay": request_delay,
    }

    if args.noui:
        return run_batch(
            args,
            camera_ip,
            camera_config,
            args.name or camera_ip,
            state_path,
            backup_dir,
            config_path,
            logger,
        )

    try:
        server = ConsoleServer(
            (args.bind, args.port),
            camera_config,
            name=args.name,
            state_path=state_path,
            allow_hosts=args.allow_host,
            backup_dir=backup_dir,
        )
    except OSError as error:
        print(
            "cannot bind {}:{}: {}".format(args.bind, args.port, error),
            file=sys.stderr,
        )
        return EXIT_BIND

    urls = console_urls(args.bind, server.server_address[1])
    print("Amcrest console for {} ({})".format(args.name or camera_ip, camera_ip))
    print("Listening on {}:{} (login required).".format(args.bind, server.server_address[1]))
    print("Mirror: {}".format(state_path))
    print("Backups: {}".format(backup_dir))
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
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
