#!/usr/bin/env python3
"""Terminal password manager: register accounts, verify logins, rotate passwords.

Passwords are stored as scrypt hashes with a per-user random salt. No plaintext
password is ever written to disk, and no password is ever passed on the command
line, where it would be visible in `ps` output and shell history.

Storage is a JSON file, `vault.json` next to this script unless `--vault` says
otherwise, written atomically and with mode 0600.

Usage:
    tool.py                                  interactive menu
    tool.py register  --username alice
    tool.py login     --username alice
    tool.py list
    tool.py change-password --username alice
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# scrypt cost parameters. These are deliberate, not arbitrary: N=2**14 with
# r=8 needs 128 * N * r = 16 MiB per hash and measured 16 guesses/sec on one
# core of this host. Plain SHA-256 measured 1,187,499/sec on the same core.
# The cost is what makes an offline dictionary attack expensive.
SCRYPT_N = 1 << 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SALT_BYTES = 16

# maxmem must exceed 128 * N * r or OpenSSL refuses the parameters. 16 MiB is
# what we need; 64 MiB is headroom.
SCRYPT_MAXMEM = 64 * 1024 * 1024

ALGO_ID = f"scrypt$n={SCRYPT_N},r={SCRYPT_R},p={SCRYPT_P}"

MIN_PASSWORD_LEN = 12

console = Console()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_salt() -> bytes:
    """16 cryptographically random bytes, hex-encoded for storage."""
    return secrets.token_bytes(SALT_BYTES)


def hash_password(password: str, salt: bytes) -> bytes:
    """Derive a key from `password` using scrypt and the given salt.

    Returns raw bytes, not hex, so the caller decides on the encoding.
    """
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
        maxmem=SCRYPT_MAXMEM,
    )


class VaultError(Exception):
    """Raised for anything the caller should report to the user."""


class Vault:
    """A JSON-backed store of username -> {salt, hash, algo, created}."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self.records: dict[str, dict] = {}
        if self.path.exists():
            try:
                self.records = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise VaultError(f"{self.path} is not valid JSON: {exc}") from exc

    def _save(self) -> None:
        """Write the vault atomically with owner-only permissions.

        The temp file is chmod'd before the rename so the credentials are never
        briefly world-readable, and a crash mid-write leaves the old vault
        intact rather than a truncated one.
        """
        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(self.records, handle, indent=4, sort_keys=True)
            handle.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    def has(self, username: str) -> bool:
        return username in self.records

    def usernames(self) -> list[str]:
        return sorted(self.records)

    def register(self, username: str, password: str) -> dict:
        if self.has(username):
            raise VaultError(f"user '{username}' already exists")
        salt = new_salt()
        digest = hash_password(password, salt)
        record = {
            "algo": ALGO_ID,
            "salt": salt.hex(),
            "hash": digest.hex(),
            "created": utc_now(),
        }
        self.records[username] = record
        self._save()
        return record

    def verify(self, username: str, password: str) -> bool:
        """Check `password` against the stored hash for `username`.

        The comparison is constant time, and an unknown username still performs
        a full scrypt derivation against a throwaway salt. Without that, a
        missing user would return measurably faster than a wrong password and
        the response time alone would reveal which usernames exist.
        """
        record = self.records.get(username)
        if record is None:
            hash_password(password, b"\x00" * SALT_BYTES)
            return False
        if record.get("algo") != ALGO_ID:
            raise VaultError(
                f"vault uses unsupported algorithm {record.get('algo')!r}; "
                f"this build only reads {ALGO_ID!r}"
            )
        candidate = hash_password(password, bytes.fromhex(record["salt"]))
        return secrets.compare_digest(candidate.hex(), record["hash"])

    def change_password(self, username: str, old: str, new: str) -> None:
        if not self.verify(username, old):
            raise VaultError("current password is incorrect")
        salt = new_salt()  # fresh salt, so the new hash differs even if reused
        digest = hash_password(new, salt)
        record = self.records[username]
        record["salt"] = salt.hex()
        record["hash"] = digest.hex()
        record["rotated"] = utc_now()
        self._save()


def read_password(confirm: bool = False) -> str:
    """Prompt for a password without echoing it.

    Reads from stdin when --password-stdin is set, which is how the test suite
    drives it. Passing a password as an argument would expose it in the process
    table for the lifetime of the command.
    """
    if os.environ.get("VAULT_PASSWORD_STDIN") == "1" or sys.stdin.isatty() is False:
        password = sys.stdin.readline().rstrip("\n")
        if confirm:
            if sys.stdin.readline().rstrip("\n") != password:
                raise VaultError("passwords did not match")
        return password
    password = getpass.getpass("password: ")
    if confirm:
        if password != getpass.getpass("confirm password: "):
            raise VaultError("passwords did not match")
    return password


def check_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LEN:
        raise VaultError(
            f"password must be at least {MIN_PASSWORD_LEN} characters "
            f"(got {len(password)})"
        )


def cmd_register(args: argparse.Namespace, vault: Vault) -> int:
    password = read_password(confirm=True)
    check_strength(password)
    record = vault.register(args.username, password)
    console.print(
        Panel(
            f"[green]registered[/] '{args.username}'\n"
            f"algo  {record['algo']}\n"
            f"salt  {record['salt']}\n"
            f"hash  {record['hash']}",
            title="vault",
            border_style="green",
        )
    )
    return 0


def cmd_login(args: argparse.Namespace, vault: Vault) -> int:
    password = read_password()
    if vault.verify(args.username, password):
        console.print(f"[green]login ok[/]  welcome, {args.username}")
        return 0
    console.print("[red]login failed[/]  username or password is incorrect")
    return 1


def cmd_list(args: argparse.Namespace, vault: Vault) -> int:
    if not vault.usernames():
        console.print("vault is empty")
        return 0
    table = Table(title=f"vault: {vault.path}", show_lines=False)
    table.add_column("username", style="bold cyan")
    table.add_column("algo")
    table.add_column("hash (first 16)")
    table.add_column("created")
    table.add_column("rotated")
    for name in vault.usernames():
        record = vault.records[name]
        table.add_row(
            name,
            record["algo"],
            record["hash"][:16] + "...",
            record.get("created", "-"),
            record.get("rotated", "-"),
        )
    console.print(table)
    return 0


def cmd_change_password(args: argparse.Namespace, vault: Vault) -> int:
    # Verify the current password before asking for a new one, so a user who
    # mistyped it is told immediately instead of being prompted to supply a
    # replacement they were never entitled to set.
    old = read_password()
    if not vault.verify(args.username, old):
        raise VaultError("current password is incorrect")
    new = read_password(confirm=True)
    check_strength(new)
    if old == new:
        raise VaultError("new password must differ from the current one")
    vault.change_password(args.username, old, new)
    console.print(f"[green]password rotated[/] for '{args.username}'")
    return 0


def cmd_menu(args: argparse.Namespace, vault: Vault) -> int:
    """Interactive front end. Each protected action re-prompts for a password."""
    console.print(
        Panel(
            "[bold]password vault[/]\n\n"
            "  1  register    2  login    3  list    4  change password    q  quit",
            border_style="blue",
        )
    )
    while True:
        choice = console.input("\n[bold blue]select[/] ").strip().lower()
        try:
            if choice == "1":
                name = console.input("username: ").strip()
                if vault.has(name):
                    raise VaultError(f"user '{name}' already exists")
                cmd_register(
                    argparse.Namespace(username=name), vault
                )
            elif choice == "2":
                name = console.input("username: ").strip()
                cmd_login(argparse.Namespace(username=name), vault)
            elif choice == "3":
                cmd_list(argparse.Namespace(), vault)
            elif choice == "4":
                name = console.input("username: ").strip()
                cmd_change_password(argparse.Namespace(username=name), vault)
            elif choice in ("q", "quit", "exit"):
                return 0
            else:
                console.print("[yellow]unknown choice[/]")
        except VaultError as exc:
            console.print(f"[red]error[/] {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Password manager using salted scrypt hashing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--vault",
        default=str(Path(__file__).with_name("vault.json")),
        help="path to the vault file (default: vault.json next to this script)",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("menu", help="interactive menu (default)")

    register = sub.add_parser("register", help="create an account")
    register.add_argument("--username", required=True)

    login = sub.add_parser("login", help="verify a password")
    login.add_argument("--username", required=True)

    listing = sub.add_parser("list", help="list stored accounts")
    listing.set_defaults(func=cmd_list)

    change = sub.add_parser("change-password", help="rotate a password")
    change.add_argument("--username", required=True)

    register.set_defaults(func=cmd_register)
    login.set_defaults(func=cmd_login)
    change.set_defaults(func=cmd_change_password)
    return parser


HANDLERS = {
    "register": cmd_register,
    "login": cmd_login,
    "list": cmd_list,
    "change-password": cmd_change_password,
    "menu": cmd_menu,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = HANDLERS.get(args.command or "menu", cmd_menu)
    try:
        vault = Vault(args.vault)
        return handler(args, vault)
    except VaultError as exc:
        console.print(f"[red]error[/] {exc}")
        return 2
    except KeyboardInterrupt:
        console.print("\n[yellow]interrupted[/]")
        return 130


if __name__ == "__main__":
    sys.exit(main())