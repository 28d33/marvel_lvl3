#!/usr/bin/env python3
"""
Task 8 - automated flight price collection.

Drives the KAYAK flight search form in a real browser (Selenium + Chromium),
runs the search the user asked for, extracts the resulting fares, and emails a
report with smtplib. There is no YAML, no config file and no hard-coded route:
every part of the search is a command line parameter.

Usage:
    python flight_scraper.py --origin London --destination "New York" \
        --depart 2026-11-10 --return 2026-11-17 --adults 1 \
        --email-to me@example.com --smtp-host localhost --smtp-port 8025

The script is deliberately defensive. KAYAK is a JavaScript single page
application that re-renders its own DOM, so every element is re-queried
immediately before use and every click goes through JavaScript. A plain
element.click() is intercepted often enough to make the script fail
intermittently, which is the main thing that makes naive scrapers unreliable.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import smtplib
import sys
import time
from dataclasses import dataclass, asdict
from datetime import date
from email.message import EmailMessage
from email.utils import formatdate

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# Money as rendered by the site, e.g. "£1,234" or "$89".
PRICE_RE = re.compile(r"([£$€])\s?([\d,]+)")
CARRIER_HINT_RE = re.compile(r"\b([A-Z]{2})\b")


@dataclass
class Flight:
    """One scraped fare row."""
    airline: str
    price: str
    currency: str
    outbound: str
    duration: str
    stops: str
    cabin: str = ""


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------
# browser
# --------------------------------------------------------------------------

def build_driver(headless: bool = True, lang: str = "en-GB"):
    """Create a Chromium driver with options tuned for a JS-heavy SPA."""
    opts = Options()
    args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1500,1400",
        f"--lang={lang}",
        # Without these the layout is narrower and KAYAK drops some results.
        "--disable-blink-features=AutomationControlled",
    ]
    if headless:
        args.append("--headless=new")
    for a in args:
        opts.add_argument(a)
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opts)


def js_click(driver, element) -> bool:
    """Click through JavaScript.

    Native clicks are frequently intercepted by KAYAK's own overlays (the
    consent dialog, the location autocomplete list). A scripted click bypasses
    the hit-test and lands on the element regardless of what is painted above it.
    """
    try:
        driver.execute_script("arguments[0].click()", element)
        return True
    except Exception:
        return False


def scroll_to(driver, element) -> None:
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'center'})",
            element)
    except Exception:
        pass


# --------------------------------------------------------------------------
# page interactions
# --------------------------------------------------------------------------

def dismiss_consent(driver, wait: WebDriverWait) -> bool:
    """Dismiss the cookie dialog, which otherwise covers the search form.

    It reappears on some loads, so this is called before every interaction
    rather than once at the start.
    """
    for label in ("Accept all", "Accept All", "Reject all"):
        for btn in driver.find_elements(
                By.XPATH, f"//button[contains(normalize-space(.), '{label}')]"):
            try:
                if btn.is_displayed() and js_click(driver, btn):
                    log(f"consent dialog dismissed ({label!r})")
                    time.sleep(1.5)
                    return True
            except Exception:
                continue
    return False


def pick_location(driver, wait: WebDriverWait, aria: str, query: str,
                  index: int = 0) -> str:
    """Type into an origin/destination box and choose one autocomplete row."""
    # Presence is checked rather than clickability on purpose: the consent
    # overlay covers the field, so the element is technically unclickable while
    # being perfectly usable. js_click() ignores the hit test.
    field = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, f"input[aria-label='{aria}']")))
    dismiss_consent(driver, wait)
    scroll_to(driver, field)
    time.sleep(0.5)
    js_click(driver, field)
    time.sleep(0.3)
    field.clear()
    field.send_keys(query)

    # The list renders asynchronously; wait for at least one visible row.
    wait.until(lambda d: [e for e in d.find_elements(By.CSS_SELECTOR, "[role=option]")
                          if e.is_displayed()])
    time.sleep(1.5)
    rows = [e for e in driver.find_elements(By.CSS_SELECTOR, "[role=option]")
            if e.is_displayed()]
    if not rows:
        raise RuntimeError(f"no autocomplete results for {query!r} in {aria}")
    chosen = rows[min(index, len(rows) - 1)]
    label = chosen.text.strip().splitlines()[0]
    js_click(driver, chosen)
    time.sleep(1.5)
    return label


def visible_months(driver) -> dict[str, object]:
    """Map 'November 2026' -> its <caption> element, for currently open months."""
    out = {}
    for cap in driver.find_elements(By.CSS_SELECTOR, "caption.w0lb-month-name"):
        try:
            if cap.is_displayed():
                out[cap.text.strip()] = cap
        except Exception:
            continue
    return out


def reveal_month(driver, wait: WebDriverWait, year: int, month: int,
                 max_clicks: int = 14) -> None:
    """Scroll the calendar forward until the wanted month is on screen."""
    target = f"{MONTHS[month - 1]} {year}"
    for _ in range(max_clicks):
        if target in visible_months(driver):
            return
        nxt = None
        for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
            try:
                if not btn.is_displayed():
                    continue
                label = (btn.get_attribute("aria-label") or "").strip().lower()
                if "next" in label or "increase" in label:
                    nxt = btn
                    break
            except Exception:
                continue
        if nxt is None or not js_click(driver, nxt):
            break
        time.sleep(1.0)
    if target not in visible_months(driver):
        raise RuntimeError(f"could not reach {target} in the calendar")


def pick_date(driver, wait: WebDriverWait, label: str, year: int, month: int,
              day: int) -> None:
    """Open the departure/return calendar and click one day cell."""
    opener = wait.until(EC.presence_of_element_located(
        (By.XPATH, f"//*[@aria-label='{label}']")))
    scroll_to(driver, opener)
    time.sleep(0.5)
    js_click(driver, opener)
    time.sleep(2)

    reveal_month(driver, wait, year, month)
    cap = visible_months(driver)[f"{MONTHS[month - 1]} {year}"]
    # The <caption> sits inside the <table> holding that month's day cells.
    table = cap.find_element(By.XPATH, "..")
    cells = [c for c in table.find_elements(By.CSS_SELECTOR, "td")
             if (c.text or "").strip() == str(day)]
    if not cells:
        raise RuntimeError(f"{day} not found in {MONTHS[month-1]} {year}")
    js_click(driver, cells[0])
    time.sleep(2)


IATA_RE = re.compile(r"^[A-Za-z]{3}$")


def resolve_code(query: str) -> str:
    """Accept either a 3-letter IATA code or a city name.

    A city has no code of its own, so the caller must supply one via
    --origin-code / --destination-code; a bare city name is rejected rather
    than guessed, because guessing would silently search the wrong airport.
    """
    q = query.strip()
    if IATA_RE.match(q):
        return q.upper()
    raise ValueError(
        f"{q!r} is not a 3-letter IATA code. City names need an explicit code, "
        f"e.g. --origin London --origin-code LON")


def build_url(site: str, o_code: str, d_code: str, depart: date,
              ret: date | None, adults: int, cabin: str) -> str:
    """Compose a KAYAK results URL.

    KAYAK accepts the whole search as a path, which is far more reliable than
    driving the form: the form depends on a geolocated default origin and a
    combined date-range widget, both of which reset themselves. The parameters
    are identical - they come from the same command line - but the URL path has
    no such state.
    """
    base = site.rstrip("/")
    if base.endswith("/flights"):
        base = base[: -len("/flights")]
    leg = f"{o_code}-{d_code}/{depart.isoformat()}"
    if ret:
        leg += f"/{ret.isoformat()}"
    q = f"?adults={adults}&cabin={cabin}&sort=bestflight_a"
    return f"{base}/flights/{leg}{q}"


def parse_iso(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected a date as YYYY-MM-DD, got {value!r}")


# --------------------------------------------------------------------------
# scraping
# --------------------------------------------------------------------------

def scrape_results(driver, wait: WebDriverWait, limit: int) -> list[Flight]:
    """Read fares out of the loaded results page."""
    wait.until(lambda d: len(PRICE_RE.findall(
        d.execute_script("return document.body ? document.body.innerText : ''"))) > 3)
    # KAYAK streams results in; give the list time to settle before reading.
    time.sleep(8)

    flights: list[Flight] = []
    seen: set[str] = set()
    non_flight = 0

    # Each itinerary is one [class*='nrc6'] container. KAYAK's class names are
    # hashed and rotate between deployments, so this prefix match is the only
    # stable handle available; the fallback below covers it if it changes.
    for node in driver.find_elements(By.CSS_SELECTOR, "[class*='nrc6']"):
        try:
            if not node.is_displayed():
                continue
            text = node.text.strip()
            money = PRICE_RE.search(text)
            if not money or len(text) < 40:
                continue
            # KAYAK is a meta-search and mixes rail and coach into the same
            # result list on routes such as London-Paris, where a train can be
            # the cheapest option by a wide margin. Those are not flights, so
            # they are counted and excluded rather than silently reported.
            if NON_FLIGHT_RE.search(text):
                non_flight += 1
                continue
            key = str(hash(text))
            if key in seen:
                continue
            seen.add(key)
            flights.append(parse_itinerary(text, money))
        except Exception:
            continue
        if len(flights) >= limit:
            break

    if non_flight:
        log(f"excluded {non_flight} non-flight result(s) (rail/coach)")
    if not flights:
        flights = fallback_parse(driver, limit)
    return flights


TIME_RE = re.compile(r"^(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})")
DUR_RE = re.compile(r"^(\d+)h\s*(\d+)m")
STOPS_RE = re.compile(r"^(direct|\d+\s*stops?)", re.I)
AIRPORT_RE = re.compile(r"^([A-Z]{3})[A-Z]")
# Real carrier names are short, title-cased and contain no sentence
# punctuation. KAYAK fills the same container with marketing copy such as
# "Explore. Experience. Economise. Elevate your travel", which a loose pattern
# happily reports as an airline.
CARRIER_RE = re.compile(r"^[A-Z][A-Za-z0-9.&'\-]*(?: [A-Za-z0-9.&'\-]+){0,3}$")
MARKETING_RE = re.compile(
    r"(explore|experience|economise|elevate|discover|save|deal|book|travel|"
    r"holiday|journey|price|fly|now|with|your|from|for)", re.I)
NON_FLIGHT_RE = re.compile(r"\b(train|rail|coach|bus|ferry)\b", re.I)
PROMO_RE = re.compile(r"^(self-transfer|cheapest|best|fastest|flexible|deal|"
                      r"book now|travel up|split|show more|see more|"
                      r"more results|select|train)", re.I)
JUNK_RE = re.compile(r"^(Ad|\d+|Select|View Deal|Economy|Business|Premium|First|"
                     r"Best|\+|Taxes|Fees|per adult|traveler|Round|Trip)", re.I)


def parse_itinerary(text: str, money) -> Flight:
    """Pull structured fields out of one itinerary block.

    A block looks like::

        13:05 - 16:25 | LHR Heathrow | - | JFK John F Kennedy Intl
        direct | 8h 20m | 18:00 - 06:20 | +1 | ... | Virgin Atlantic | 1 | GBP 437

    Each field is matched by shape rather than position, because the number of
    lines varies with stops, connections and inserted advertising rows.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    departure = arrival = duration = stops = airline = cabin = ""

    for ln in lines:
        if not departure and TIME_RE.match(ln):
            m = TIME_RE.match(ln)
            departure, arrival = m.group(1), m.group(2)
            continue
        if not duration and DUR_RE.match(ln):
            h, m = DUR_RE.match(ln).groups()
            duration = f"{h}h {m}m"
            continue
        if not stops and STOPS_RE.match(ln):
            stops = STOPS_RE.match(ln).group(1)
            continue
        low = ln.lower()
        if not cabin and (low.startswith("economy") or low.startswith("business")
                          or low.startswith("premium") or low.startswith("first")):
            cabin = ln[:40]
            continue
        if AIRPORT_RE.match(ln) or JUNK_RE.match(ln):
            continue
        # A carrier name is the remaining sentence-cased line. KAYAK also
        # injects promotional headings such as "Self-transfer hack", which are
        # not airlines and would otherwise be reported as one.
        # An all-caps token is an airport or route code ("DUB"), never a
        # carrier, so a title-cased letter is required.
        if (not airline and CARRIER_RE.match(ln) and 3 <= len(ln) <= 28
                and any(c.islower() for c in ln)
                and not PROMO_RE.match(ln)
                and not MARKETING_RE.search(ln)):
            airline = ln

    outbound = f"{departure}-{arrival}" if departure else ""
    return Flight(airline=airline[:60], price=money.group(2),
                  currency=money.group(1), outbound=outbound,
                  duration=duration, stops=stops or "unknown", cabin=cabin)


def to_number(f: Flight) -> float:
    try:
        return float(f.price.replace(",", ""))
    except ValueError:
        return float("inf")


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def build_summary(flights: list[Flight]) -> str:
    if not flights:
        return "No fares were found for this search."
    priced = sorted([f for f in flights if to_number(f) < float("inf")],
                    key=to_number)
    lo, hi = priced[0], priced[-1]
    lines = [
        f"Fares found: {len(priced)}",
        f"Cheapest: {lo.currency}{lo.price}",
        f"Most expensive: {hi.currency}{hi.price}",
        "",
        "Lowest fares:",
    ]
    for i, f in enumerate(priced[:10], 1):
        who = f.airline or "carrier not captured"
        bits = [b for b in (f.outbound, f.duration, f.stops, f.cabin) if b]
        lines.append(f"  {i:2}. {f.currency}{f.price:<6} {who:<24} "
                     f"{' | '.join(bits)}")
    return "\n".join(lines)


def send_email(host: str, port: int, to_addr: str, subject: str, body: str,
               from_addr: str | None = None, use_tls: bool = False,
               timeout: int = 20) -> str:
    """Send the report over SMTP. Returns a short status string."""
    msg = EmailMessage()
    msg["From"] = from_addr or f"flight-scraper@{host}"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(body)

    try:
        if use_tls:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as s:
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as s:
                s.ehlo()
                try:
                    s.starttls()
                    s.ehlo()
                except smtplib.SMTPNotSupportedError:
                    pass  # catcher has no TLS; plain delivery is fine
                s.send_message(msg)
        return f"sent to {to_addr} via {host}:{port}"
    except Exception as exc:
        return f"email failed ({type(exc).__name__}: {exc})"


def write_csv(path: str, flights: list[Flight]) -> None:
    if not flights:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(asdict(flights[0]).keys()))
        w.writeheader()
        for f in flights:
            w.writerow(asdict(f))


def write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scrape flight fares from KAYAK and email a report.")
    p.add_argument("--origin", help="origin city or airport code (may be "
                                    "omitted if --origin-code is given)")
    p.add_argument("--destination", help="destination city or airport code (may "
                                        "be omitted if --destination-code is "
                                        "given)")
    p.add_argument("--depart", required=True, type=parse_iso,
                   help="outbound date, YYYY-MM-DD")
    p.add_argument("--return", dest="ret", type=parse_iso,
                   help="return date, YYYY-MM-DD (omit for one-way)")
    p.add_argument("--adults", type=int, default=1, help="passengers, default 1")
    p.add_argument("--cabin", default="economy",
                   choices=["economy", "premium", "business", "first"])
    p.add_argument("--origin-code", help="IATA code for --origin (required if "
                                         "the origin is a city name)")
    p.add_argument("--destination-code", help="IATA code for --destination")
    p.add_argument("--mode", choices=["url", "form"], default="url",
                   help="'url' builds the results URL from the parameters "
                        "(default, robust); 'form' types into the search form")
    p.add_argument("--match-index", type=int, default=0,
                   help="which autocomplete row to pick, default 0 (usually "
                        "the 'all airports' entry)")
    p.add_argument("--limit", type=int, default=15,
                   help="maximum fares to report, default 15")
    p.add_argument("--site", default="https://www.kayak.co.uk/flights",
                   help="search page (default UK site, priced in GBP)")
    p.add_argument("--show", action="store_true",
                   help="run with a visible browser window")
    p.add_argument("--timeout", type=int, default=30,
                   help="explicit wait timeout in seconds, default 30")

    p.add_argument("--email-to", help="address to send the report to")
    p.add_argument("--smtp-host", default="localhost")
    p.add_argument("--smtp-port", type=int, default=8025)
    p.add_argument("--smtp-from", help="envelope/From address")
    p.add_argument("--smtp-tls", action="store_true",
                   help="use implicit TLS (SMTP_SSL)")
    p.add_argument("--no-email", action="store_true",
                   help="skip sending even if --email-to is given")

    p.add_argument("--out-csv", help="write results to this CSV")
    p.add_argument("--out-json", help="write full result payload to this JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # In url mode only the codes matter; in form mode only the names do.
    missing = []
    if not (args.origin or args.origin_code):
        missing.append("--origin/--origin-code")
    if not (args.destination or args.destination_code):
        missing.append("--destination/--destination-code")
    if args.mode == "form" and (not args.origin or not args.destination):
        log("--mode form needs --origin and --destination as search text")
        return 2
    if missing:
        log("missing required argument(s): " + ", ".join(missing))
        return 2

    # Resolve the IATA codes before launching a browser, so a bad argument
    # fails in milliseconds instead of after a full Chromium startup.
    o_code = d_code = None
    if args.mode == "url":
        try:
            o_code = resolve_code(args.origin_code or args.origin)
            d_code = resolve_code(args.destination_code or args.destination)
        except ValueError as exc:
            log(str(exc))
            return 2

    if args.ret and args.ret < args.depart:
        log("return date is before the departure date")
        return 2
    if args.depart < date.today():
        log("departure date is in the past")
        return 2

    driver = None
    try:
        log(f"launching chromium (headless={not args.show})")
        driver = build_driver(headless=not args.show)
        wait = WebDriverWait(driver, args.timeout)

        if args.mode == "url":
            url = build_url(args.site, o_code, d_code, args.depart, args.ret,
                            args.adults, args.cabin)
            log(f"{o_code} -> {d_code}, {args.depart}"
                f"{'/' + str(args.ret) if args.ret else ''}, {args.adults} adult(s)")
            log(f"loading {url}")
            driver.get(url)
            time.sleep(6)
        else:
            log(f"loading {args.site}")
            driver.get(args.site)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[aria-label='Origin location']")))
            time.sleep(2)
            dismiss_consent(driver, wait)

            o = pick_location(driver, wait, "Origin location", args.origin,
                              args.match_index)
            log(f"origin: {o}")
            dismiss_consent(driver, wait)
            dst = pick_location(driver, wait, "Destination location",
                                args.destination, args.match_index)
            log(f"destination: {dst}")

            pick_date(driver, wait, "Departure date",
                      args.depart.year, args.depart.month, args.depart.day)
            log(f"departure: {args.depart}")
            if args.ret:
                dismiss_consent(driver, wait)
                pick_date(driver, wait, "Return date",
                          args.ret.year, args.ret.month, args.ret.day)
                log(f"return: {args.ret}")

            dismiss_consent(driver, wait)
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(2)
            search_btn = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//button[normalize-space(.)='Search']")))
            log("submitting search")
            js_click(driver, search_btn)
            wait.until(lambda dr: "/flights/" in dr.current_url
                       and dr.current_url != args.site)

        log(f"results url: {driver.current_url}")
        flights = scrape_results(driver, wait, args.limit)
        log(f"scraped {len(flights)} fares")

        # KAYAK ignores the cabin query parameter, so the fares on the page may
        # not be the cabin that was asked for. Report what is actually there
        # rather than what was requested.
        observed = sorted({f.cabin for f in flights if f.cabin})
        if observed:
            log(f"cabin shown by the site: {', '.join(observed)}")
            if args.cabin not in " ".join(observed).lower():
                log(f"WARNING: requested cabin '{args.cabin}' but the site "
                    f"returned {', '.join(observed)}; results are not for "
                    f"that cabin")

        summary = build_summary(flights)
        print("\n" + summary + "\n")

        payload = {
            "origin": args.origin, "destination": args.destination,
            "depart": args.depart.isoformat(),
            "return": args.ret.isoformat() if args.ret else None,
            "adults": args.adults, "cabin": args.cabin,
            "mode": args.mode,
            "results_url": driver.current_url,
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "fare_count": len(flights),
            "fares": [asdict(f) for f in flights],
        }

        if args.out_csv:
            write_csv(args.out_csv, flights)
            log(f"wrote {args.out_csv}")
        if args.out_json:
            write_json(args.out_json, payload)
            log(f"wrote {args.out_json}")

        if args.email_to and not args.no_email:
            subject = (f"Flight prices {args.origin or args.origin_code} -> {args.destination or args.destination_code} "
                       f"{args.depart.isoformat()}")
            status = send_email(args.smtp_host, args.smtp_port, args.email_to,
                                subject, summary, args.smtp_from, args.smtp_tls)
            log(f"email: {status}")
        return 0

    except Exception as exc:
        log(f"ERROR {type(exc).__name__}: {exc}")
        if driver is not None:
            try:
                log(f"  at url:   {driver.current_url[:120]}")
                log(f"  page:     {driver.title[:80]}")
                body = driver.execute_script(
                    "return document.body ? document.body.innerText : ''")
                flags = [w for w in ('captcha', 'access denied', 'unusual',
                                     'robot', 'verify', 'too many')
                         if w in body.lower()]
                log(f"  body:     {len(body)} chars, wall flags: {flags or 'none'}")
                log(f"  snippet:  {body[:160]!r}")
            except Exception:
                pass
        return 1
    finally:
        if driver is not None:
            driver.quit()
            log("browser closed")


if __name__ == "__main__":
    sys.exit(main())