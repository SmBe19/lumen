"""Command line entry point.

Usage:
    lumen                       # run the development server
    lumen add-teacher <name>    # add / update a teacher account
    lumen list-teachers         # list teacher accounts
"""

from __future__ import annotations

import argparse
import getpass
import sys

from . import store


def _add_teacher(args: argparse.Namespace) -> int:
    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            return 1
    try:
        store.add_teacher(args.username, password)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Teacher '{args.username}' saved to {store.teachers_file()}.")
    return 0


def _list_teachers(_args: argparse.Namespace) -> int:
    teachers = store.load_teachers()
    if not teachers:
        print("No teacher accounts configured.")
        return 0
    for username in sorted(teachers):
        print(username)
    return 0


def _run_server(args: argparse.Namespace) -> int:
    from .app import create_app

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lumen", description="Screen monitoring for exams")
    sub = parser.add_subparsers(dest="command")

    add = sub.add_parser("add-teacher", help="add or update a teacher account")
    add.add_argument("username")
    add.add_argument("--password", help="password (otherwise prompted)")
    add.set_defaults(func=_add_teacher)

    listing = sub.add_parser("list-teachers", help="list teacher accounts")
    listing.set_defaults(func=_list_teachers)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Default to running the server when no known subcommand is given.
    known = {"add-teacher", "list-teachers", "-h", "--help"}
    if not argv or argv[0] not in known:
        parser = argparse.ArgumentParser(prog="lumen")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=5000)
        parser.add_argument("--debug", action="store_true")
        args = parser.parse_args(argv)
        return _run_server(args)

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
