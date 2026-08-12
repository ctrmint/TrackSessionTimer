#!/usr/bin/env python3
"""Deploy the repository's flat firmware payload to a MicroPython device."""

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIRMWARE_ROOT = REPOSITORY_ROOT / "firmware"
ENTRY_POINT = FIRMWARE_ROOT / "main.py"
USER_CONFIG = FIRMWARE_ROOT / "user.json"
DEPLOYED_SUFFIXES = {".py", ".json", ".bin", ".rgb565"}


def support_files(include_user=False):
    """Return deterministic payload paths, excluding the entry point."""
    excluded = {ENTRY_POINT}
    if not include_user:
        excluded.add(USER_CONFIG)
    return tuple(
        path
        for path in sorted(FIRMWARE_ROOT.iterdir(), key=lambda item: item.name)
        if path.is_file()
        and path.suffix in DEPLOYED_SUFFIXES
        and path not in excluded
    )


def mpremote_command(arguments, port, executable=None):
    """Build one mpremote command without relying on the current directory."""
    return [
        executable or sys.executable,
        "-m",
        "mpremote",
        "connect",
        port,
        *[str(argument) for argument in arguments],
    ]


def deployment_commands(port="auto", include_user=False, executable=None):
    """Build ordered copy and reset commands; main.py is always copied last."""
    files = support_files(include_user=include_user)
    return (
        mpremote_command(
            ("fs", "cp", *files, ":"),
            port,
            executable=executable,
        ),
        mpremote_command(
            ("fs", "cp", ENTRY_POINT, ":"),
            port,
            executable=executable,
        ),
        mpremote_command(("reset",), port, executable=executable),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port",
        default="auto",
        help="mpremote connection target (default: auto)",
    )
    parser.add_argument(
        "--include-user",
        action="store_true",
        help="install firmware/user.json; use only for a fresh or reset device",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the ordered commands without connecting to a device",
    )
    args = parser.parse_args()

    commands = deployment_commands(
        port=args.port,
        include_user=args.include_user,
    )
    for command in commands:
        print(shlex.join(command))
        if not args.dry_run:
            subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
