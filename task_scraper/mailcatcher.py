#!/usr/bin/env python3
"""
Loopback SMTP catcher for Task 8.

Runs an unauthenticated SMTP server on 127.0.0.1 and writes every message it
receives to disk as a .eml file, printing a one-line summary. It exists so the
scraper can exercise the real smtplib path - envelope, headers, MIME body -
without sending anything off the machine or needing real credentials.

    python mailcatcher.py --port 8025 --outdir /tmp/maildrop

Stop with Ctrl-C. The scraped report can then be inspected with:

    python -m email --policy=default /tmp/maildrop/*.eml
"""

from __future__ import annotations

import argparse
import asyncio
import email
import os
import sys
from datetime import datetime, timezone

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message


class CapturingHandler(Message):
    """Print a short summary and persist the raw message."""

    def __init__(self, outdir: str):
        super().__init__()
        self.outdir = outdir
        self.count = 0

    async def handle_message(self, message: email.message.Message):
        """aiosmtpd parses the message before handing it over."""
        self.count += 1
        msg = message
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        name = f"{stamp}-{self.count:03d}.eml"
        path = os.path.join(self.outdir, name)
        with open(path, "wb") as fh:
            fh.write(msg.as_bytes())

        frm = msg.get("From", "?")
        to = msg.get("To", "?")
        subj = msg.get("Subject", "(no subject)")

        if msg.is_multipart():
            body = ""
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True) or b""
                    body = payload.decode(part.get_content_charset() or "utf-8",
                                          errors="replace")
                    break
        else:
            payload = msg.get_payload(decode=True) or b""
            body = payload.decode(msg.get_content_charset() or "utf-8",
                                  errors="replace")

        print(f"\n=== message {self.count} ===", flush=True)
        print(f"  From     : {frm}", flush=True)
        print(f"  To       : {to}", flush=True)
        print(f"  Subject  : {subj}", flush=True)
        print(f"  Date     : {msg.get('Date','-')}", flush=True)
        print(f"  saved    : {path}", flush=True)
        print("  " + "-" * 60, flush=True)
        for line in body.splitlines():
            print(f"  | {line}", flush=True)
        print("  " + "-" * 60, flush=True)
        return "250 Message accepted for delivery"

    async def handle_DATA(self, server, session, envelope):
        self.count += 1
        raw = envelope.content
        msg = email.message_from_bytes(raw)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        name = f"{stamp}-{self.count:03d}.eml"
        path = os.path.join(self.outdir, name)
        with open(path, "wb") as fh:
            fh.write(raw)

        frm = msg.get("From", "?")
        to = msg.get("To", "?")
        subj = msg.get("Subject", "(no subject)")

        # Force a text/plain rendering so the log always shows real content.
        if msg.is_multipart():
            body = ""
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True) or b""
                    body = payload.decode(part.get_content_charset() or "utf-8",
                                          errors="replace")
                    break
        else:
            payload = msg.get_payload(decode=True) or b""
            body = payload.decode(msg.get_content_charset() or "utf-8",
                                  errors="replace")

        print(f"\n=== message {self.count} ===", flush=True)
        print(f"  envelope from : {envelope.mail_from}", flush=True)
        print(f"  envelope to   : {', '.join(envelope.rcpt_tos)}", flush=True)
        print(f"  From          : {frm}", flush=True)
        print(f"  To            : {to}", flush=True)
        print(f"  Subject       : {subj}", flush=True)
        print(f"  saved         : {path} ({len(raw)} bytes)", flush=True)
        print("  " + "-" * 60, flush=True)
        for line in body.splitlines():
            print(f"  | {line}", flush=True)
        print("  " + "-" * 60, flush=True)
        return "250 Message accepted for delivery"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8025)
    ap.add_argument("--outdir", default="/tmp/maildrop")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    handler = CapturingHandler(args.outdir)
    controller = Controller(handler, hostname=args.host, port=args.port)

    try:
        controller.start()
    except Exception as exc:
        print(f"could not bind {args.host}:{args.port} - {exc}", file=sys.stderr)
        return 1

    print(f"SMTP catcher listening on {args.host}:{args.port}")
    print(f"messages will be written to {args.outdir}")
    print("press Ctrl-C to stop", flush=True)

    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\nstopping; {handler.count} message(s) captured")
    finally:
        controller.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())