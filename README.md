# UVCE MARVEL — CL-CY-001, Level 3

## Task 1 — AWS Lambda: Two-Person Chat Application

### What I Did

Built a two-person chat app using AWS Lambda. Messages are saved to DynamoDB. The frontend is a single HTML file that runs in the browser.

| Part | Tech | Role |
|---|---|---|
| Frontend | HTML + JS | Name entry, message box, live feed |
| Backend | AWS Lambda (Python) | Handles send/receive logic |
| Database | DynamoDB | Stores all messages |
| Access | Lambda Function URL | HTTPS endpoint for the browser to call |

Tested locally with LocalStack first, then deployed to real AWS Lambda.

### How It Works

The Lambda receives a request with an `action` field:
- `send` — saves the message to DynamoDB
- `messages` — returns the last 100 messages, sorted by time

Each message is stored as: `{ id, name, message, createdAt (ms timestamp) }`.

The frontend polls for new messages every 2 seconds. It tracks already-seen message IDs so the same message isn't shown twice.

User input is set using `textContent` (not `innerHTML`) to prevent script injection.

### Deployment

- Code zipped and uploaded as a Lambda function
- DynamoDB table created separately
- Config passed via environment variables: `TABLE_NAME`, `DYNAMODB_ENDPOINT`, `AWS_DEFAULT_REGION`
- Credentials not committed — `.env` is in `.gitignore`

### Limitations

- `table.scan()` reads the whole table on every poll — fine for a small demo, but would need a proper query with a limit at scale
- CORS is open (`*`) — should be locked to a specific domain in production
- Errors are returned as plain text — fine for debugging, should be hidden in production

---


## Task 2 — CI/CD with Jenkins

### What I Did

Created a Jenkins pipeline (`Jenkinsfile`) that builds, tests, and deploys a password manager web app automatically. Jenkins runs in a container on my machine.

The app has three services:

| Service | Tech | Role |
|---|---|---|
| `db` | MySQL 8.0 | Database |
| `backend` | PHP 8.2 + Apache | REST API |
| `frontend` | nginx | Serves UI, proxies `/api/` to backend |

### Pipeline Stages

1. **Checkout** — pulls the code from the repo
2. **Build** — builds Docker images
3. **Start Services** — starts all containers with `docker compose up -d`
4. **Resolve Port** — reads the dynamic frontend port with `docker compose port frontend 80`
5. **Wait for Services** — polls the login endpoint every 2s (up to 60s) until it returns 200
6. **Test API** — logs in, extracts the auth token, calls `/api/vaults` and `/api/vaults/1/items`
7. **Health Check** — checks container status and HTTP response codes
8. **Deploy** — tags the image with the commit SHA and `latest`, pushes to a registry if credentials are set

### Notes

- The frontend uses a random port each run to avoid port conflicts between builds
- Registry push is skipped if `REGISTRY_URL`, `REGISTRY_USER`, `REGISTRY_TOKEN` are not set — build still passes
- Demo credentials are hardcoded in `docker-compose.yml` — fine for a throwaway CI stack, not for production
- The stack is never torn down between runs — a cleanup stage would make reruns fully reproducible

---

## Task 3 — SSH: Key Discovery and Transfer

### What I Did

Wrote a Bash script that SSHes into a server, finds all SSH keys on it, and copies them to a second server.

Both servers are Docker containers (built from `Dockerfile.sshd`) running real SSH daemons — source on port 2222, destination on 2223. The source was seeded with real keys: RSA, Ed25519, a `.pem`, and `authorized_keys`.

### How the Script Works (`script.sh`)

The script takes source and destination host/port/user/password as arguments. It runs 5 stages:

1. **Discover** — runs `sudo find /` on the source over SSH, looking for files matching `id_rsa*`, `id_ed25519*`, `*.pem`, `*.key`, `authorized_keys*`, `known_hosts*`. Uses `sudo` so root-owned keys aren't missed. Excludes `/proc`, `/sys`, `/etc/ssl`, `/usr` to avoid unrelated system certificates.

2. **Pack** — uploads the list of found paths to the source, then tars them all into one archive (`collected_keys.tar.gz`) on the source server.

3. **Retrieve** — downloads the archive from the source to a local staging folder.

4. **Upload** — pushes the archive to the destination server.

5. **Extract** — unpacks the archive on the destination, fixes file ownership, lists recovered files, then deletes the archive from both servers.

`sshpass` is used to supply passwords non-interactively. `StrictHostKeyChecking=no` is set so the script works with containers (which get new host keys on every rebuild).

### Verification

MD5 checksums were compared before and after — all 6 files matched:

```
source:       5575223f2ebaaf0bdccb86c93c6d0d34  deploy_key.pem
destination:  5575223f2ebaaf0bdccb86c93c6d0d34  deploy_key.pem
```

File permissions (`600`) were also preserved since `tar` stores them.

### Notes

- `StrictHostKeyChecking=no` disables host verification — necessary for containers but dangerous in real use (removes protection against man-in-the-middle attacks)
- `sshpass` exposes the password in the process list while running — not suitable for production
- `ssh_transfer/` (raw scan, path list, archive) is gitignored and not committed

---

## Task 4 — Terraform: Infrastructure as Code on AWS

### What I Did

Used Terraform to create, modify, and destroy an AWS infrastructure stack — the full build → change → destroy lifecycle. Ran against **LocalStack** (a local AWS emulator) so no real AWS account was needed.

11 resources defined in `main.tf`:

| # | Resource | Details |
|---|---|---|
| 1 | VPC | `10.0.0.0/16` |
| 2 | Subnet | `10.0.1.0/24`, public |
| 3 | Internet Gateway | — |
| 4 | Route Table | default route to gateway |
| 5 | Route Table Association | links subnet to route table |
| 6 | Security Group | ingress on ports 80, 443, 22 |
| 7 | EC2 Instance | `t3.micro`, `running` |
| 8 | S3 Bucket | `my-localstack-bucket-dev` |
| 9 | DynamoDB Table | `users-table`, on-demand billing |
| 10 | SQS Queue | `main-queue`, 4-day retention |
| 11 | SNS Topic | `main-topic` |

### Build, Change, Destroy

**Build:** `terraform init` → `validate` → `apply` — all 11 resources created. Running `plan` right after confirmed: `No changes. Your infrastructure matches the configuration.`

**Change:** Two types of changes were tested:
- Changing instance type (`t3.micro` → `t3.small`) = **in-place update**, no downtime
- Changing the bucket name = **forced replacement** (destroy old + create new), because bucket names are immutable in AWS

**Destroy:** `terraform destroy` removed all 11 resources in reverse dependency order. Verified with AWS CLI that resources were actually gone. Re-applying created new resources with **different IDs**, confirming it was a real teardown.

### Notes

- AMI is a placeholder (`ami-12345678`) — LocalStack accepts it, real AWS won't
- Port 22 is open to `0.0.0.0/0` — should be restricted to a specific IP range in production
- Credentials are hardcoded as `test`/`test` — required for LocalStack, never do this on real AWS
- `force_destroy` is not set on the S3 bucket — destroy only worked because the bucket was empty
- `terraform.tfstate` and plan files are gitignored — they can contain sensitive data

---

## Task 5 — Wireshark: Traffic Analysis and Fault Diagnosis

### What I Did

Captured my own network traffic with Wireshark while doing the Level 3 tasks. Used the capture to diagnose a real fault that was happening at the time.

**Capture file:** `marvel-l3.pcapng` — 3,585 packets, 1,705 kB, 93 seconds (Wi-Fi interface `wlp3s0`).

### Traffic Overview

| Protocol | Packets |
|---|---|
| TCP (total) | 3,181 (of which 1,492 carry TLS) |
| DNS | 184 |
| QUIC | 161 |
| UDP (other) | 69 |
| ARP / ICMPv6 | 14 |

All 92 DNS responses returned `NOERROR` — DNS was not the problem. No plaintext HTTP in the entire capture. IPv6 carried 3,213 packets vs 364 for IPv4 — this is an IPv6-preferring machine, which turned out to be the root cause of the fault.

### The Fault — LocalStack Unreachable

**Symptom:** The LocalStack emulator (local AWS emulator running on port 4566) was completely unreachable for the entire 93-second window.

**Clue from Wireshark (Statistics → Conversations → TCP):** One address received 310 out of 333 total retransmissions (93%) — all going to `64:ff9b::7f00:1` on port 4566. Zero successful connections.

**What that address means:** `64:ff9b::7f00:1` is an IPv6 address. The last 32 bits decode to `127.0.0.1`. This is a NAT64 address — the machine was trying to reach its own `localhost` over IPv6, which got routed through the NAT64 gateway instead of staying local. The SYN packets were delivered to the gateway's loopback — not the local machine — so nothing ever answered.

**Evidence it was a real failure (not a capture gap):**
- 349 SYNs sent, 0 SYN-ACKs received on port 4566
- Each connection retried with exponential backoff (1s, 2s, 4s, 8s...) before giving up after ~69 seconds
- LocalStack was running and healthy on `127.0.0.1:4566` the whole time

### Root Cause and Fix

The hostname `localhost.localstack.cloud` has two DNS records:
```
A    127.0.0.1
AAAA 64:ff9b::7f00:1
```

Because this machine prefers IPv6, it picked the AAAA record. That IPv6 address routes through the NAT64 gateway, which forwards to `127.0.0.1` on the **gateway**, not the local machine. LocalStack never received the connection.

**Fix:** Use the IPv4 literal `http://127.0.0.1:4566` instead of the hostname. The Terraform config already does this. The Lambda `handler.py` still uses the hostname — that's the one place left to fix.

### Notes

- `marvel-l3.pcapng` is not committed to this repo
- Even with all traffic encrypted, DNS queries and TLS hostnames reveal every site visited — the capture contains no credentials but is still sensitive

---

## Task 6 — Docker: Containers, Images, and Dockerfiles

### What I Did

Completed the Docker Get Started course: running containers, building images, persisting data, multi-container apps, and basics of Kubernetes. Examples below are from the Dockerfiles already in this repo.

### Key Concepts

**Image vs Container:** An image is a template. A container is a running instance of that image. Multiple containers can share the same image — in Task 3, two SSH containers were started from one image and shared the same base layers, saving disk space.

**Layers:** Each line in a Dockerfile creates a layer. Changing one line invalidates that layer and everything after it. So heavy steps (like `apt-get install`) go near the top, app code near the bottom — this way code changes don't re-run installs.

`apt-get update` and `apt-get install` are kept in a single `RUN` command so a cached (stale) package index is never used with a fresh install step.

**Common Dockerfile instructions:**
- `FROM` — base image to start from
- `RUN` — runs a command at build time (creates a layer)
- `COPY` — copies files into the image
- `WORKDIR` — sets the working directory
- `EXPOSE` — documents which port the app uses (doesn't actually publish it)

### Volumes and Networking

**Bind mounts** link a folder on the host into the container. Marked `:ro` (read-only) where the container shouldn't be able to change them (e.g. SQL schema files, nginx config).

**Named volumes** are managed by Docker and persist across container restarts. Used for the database so data survives `docker compose down`.

Containers on the same Docker network can reach each other by name. That's why nginx can say `proxy_pass http://backend:80` — Docker resolves `backend` to the right container's IP automatically.

### Docker vs Podman

This machine uses Podman behind the Docker CLI (`DOCKER_HOST` points to Podman's socket). The `docker` command works normally but is actually talking to Podman:

```
Client: Docker CLI v29.8.1
Server: Podman v5.4.2
```

| | Docker | Podman |
|---|---|---|
| Runs as | Root (daemon) | Regular user (no daemon) |
| Storage | `/var/lib/docker` | `~/.local/share/containers/storage` |
| Default network name | `bridge` | `podman` |

All commands used in Tasks 2 and 3 (`run`, `build`, `compose`, `inspect`) worked without any changes.

### Notes

- Neither Dockerfile sets a `USER` — both containers run as root inside, which is fine for this exercise but should be changed in production

---

## Task 7 — Dockerize the Web Application (No Compose File)

### What I Did

Containerized the Level 0 password manager app using only `docker run` — no `docker-compose.yml`. Three containers on one shared network: `db`, `backend`, `frontend`.

**Backend Dockerfile** (`task_docker/backend/Dockerfile`):
```dockerfile
FROM php:8.2-apache
RUN docker-php-ext-install pdo_mysql mysqli && a2enmod rewrite
WORKDIR /var/www/html
COPY backend/ /var/www/html/
RUN sed -i 's!/var/www/html!/var/www/html/public!g' /etc/apache2/sites-available/000-default.conf
EXPOSE 80
```

Database (`mysql:8.0`) and frontend (`nginx:alpine`) use stock images. All three are connected to a single bridge network named `pm-net`.

### Issues Found

**`docker build` without `--load` silently does nothing.** The build completes without error but the image isn't saved where `docker run` can find it. Must use `docker build --load` to write it to the local image store.

**Podman ignores `HEALTHCHECK` in Dockerfiles.** The instruction is stored in the image but never runs at startup. Health checks must be passed via command-line flags instead: `--health-cmd`, `--health-interval`, `--health-start-period`.

**Can't use `curl -f` for the backend health check.** The API returns `401` without a session and `404` at `/` — both cause `curl -f` to fail even when the server is working. The health check was changed to accept any HTTP response (just checking the server started), and connection refused still fails correctly.

**Rootless Podman can't bind port 80.** `-p 80:80` fails with a "privileged port" error. App runs on port `8000` instead (`-p 8000:80`).

### Storage

- Database uses a **named volume** (`pm-db-data`) — survives container restarts and rebuilds
- SQL schema/seed files mounted **read-only** into `/docker-entrypoint-initdb.d/`
- Init scripts only run when the data directory is empty — editing `schema.sql` has no effect once the volume exists

**Anonymous volume trap:** If the MySQL container is started without specifying a volume, Docker silently creates an unnamed one. Removing the container loses it forever with no error. Always use a named volume.

### Verification

Registered a user through the API, then confirmed the row was saved directly in the database:

```
POST /api/auth/register → 201, token returned
SELECT from USER table → row present with argon2id hash
```

After removing and rebuilding all containers (keeping only the named volume), the database came back with all previous data intact — init scripts did not re-run.

### Notes

- Generic container names (`db`, `backend`, `frontend`) will conflict if the Task 2 stack is also running
- The backend image is 510 MB — stored locally, not pushed

---

---

## Task 8 — Web Scraping: Flight Price Analysis

### What I Did

Built a command-line tool (`flight_scraper.py`) that searches KAYAK for flights, extracts fares, and emails a report. Uses Selenium with headless Chromium. Every search argument (origin, destination, dates, passengers) is a CLI flag.

### Why KAYAK

Tested several sites first:
- Expedia → blocked (`429 Too Many Requests`)
- Google Flights, Skyscanner, Ryanair → no prices in the page HTML
- KAYAK → serves real prices to a headless browser ✓

Note: scraping KAYAK is against their terms of use — this is for the exercise only.

### Form Mode vs URL Mode

**Form mode** (filling in the search form) failed due to two issues:
1. A cookie consent popup blocks all clicks — worked around using JavaScript clicks
2. KAYAK pre-fills the origin based on your location (Bengaluru in this case) — selecting a new city *adds* to it instead of replacing it, making the search wrong

**URL mode** (building the search URL directly) works reliably and is the default (`--mode url`). Example:
```
https://www.kayak.co.uk/flights/LON-NYC/2026-11-10/2026-11-17?adults=1&cabin=economy
```

### Bugs Found and Fixed

- **Cabin class is silently ignored by KAYAK** — requesting business class returned economy results. Tool now reads back the cabin from the page and warns if it doesn't match the request.
- **Deduplication was wrong** — keying on price + first 60 chars of description collapsed two different £437 fares into one. Fixed to use a better key.
- **KAYAK also returns trains** — a £26 London–Paris train appeared in results. Trains are now excluded.

### Results

**London → New York, 10–17 Nov 2026, 1 adult, economy:**
```
Fares found: 6 | Cheapest: £370 | Most expensive: £458

1. £370  (carrier not captured)  08:50–15:40 | 2 stops
2. £379  Virgin Atlantic         13:05–16:25 | direct
3. £436  Virgin Atlantic         09:05–12:25 | direct
4. £437  Virgin Atlantic         10:10–13:27 | direct
5. £458  Virgin Atlantic         13:05–16:25 | direct
```

**London → Paris, 1 Dec 2026, 1 way, 2 adults:** 5 fares, £68–£82, Air France and British Airways, all direct.

### Email Delivery

Report is sent via `smtplib`. For testing, `mailcatcher.py` runs a local fake SMTP server that saves emails to disk instead of sending them. 6 test emails were captured successfully.

### Input Validation

- Requires 3-letter IATA codes (rejects plain city names like "London")
- Rejects past departure dates and return dates before departure
- Exits with code `2` on bad input, `0` on success

---

## Task 9 — Hashing: Secure Password Storage & Verification

### What I Did

Built a terminal password manager (`task_hashing/tool.py`) in Python. Supports: register, login, list accounts, change password. Passwords are never stored in plain text, never logged, never passed as command-line arguments.

### Why scrypt, Not SHA-256

The original version used salted SHA-256. That's wrong for passwords — SHA-256 is fast, which is bad here:

| Algorithm | Guesses/sec |
|---|---|
| Salted SHA-256 | 1,160,012 |
| PBKDF2-SHA256 (600k iterations) | 6 |
| scrypt (what this tool uses) | 18 |

scrypt is slow **and** memory-intensive (uses 16 MB per guess). This makes brute-force attacks expensive — ~52,000× slower than SHA-256. Used `hashlib.scrypt` from stdlib (no extra install needed).

**What salting does:** makes every hash unique even if two users have the same password — defeats precomputed lookup tables.
**What salting doesn't do:** slow down an attacker. That's scrypt's job.

### Storage

Passwords are stored in `vault.json` as: `{ algo, salt, hash, timestamps }` — no plain text.

File is written atomically: write to `.tmp` → set permissions to `600` → rename into place. The permission-before-rename order matters — the reverse leaves a window where any local user can read the file.

### Login and Security Details

**Constant-time comparison:** uses `secrets.compare_digest` instead of `==` to prevent timing attacks (comparing byte by byte leaks how many characters matched).

**Timing equalisation for unknown users:** without this, "user not found" returns instantly while "wrong password" takes ~68ms — an attacker could enumerate valid usernames by timing. After the fix, both take ~65ms.

**Password change:** verifies the current password first, then generates a **new salt** and re-hashes. Using a new salt means even if the same password is reused, the stored hash changes.

**CLI:** `tool.py <command> --username alice` — exit codes `0` success, `1` wrong password/unknown user, `2` bad input.

### Limitations

- Vault is hashed JSON, not encrypted — anyone who gets the file can attack it offline
- `list` command shows hashes to any local user with no authentication
- No login lockout — rate is ~15 attempts/sec per process
- Minimum password length is 12 characters — the only rule enforced

---

## Task 10 — Nmap: Network Discovery and Port Scanning

### What I Did

I ran an Nmap scan against a /24 subnet (`xx1.202.189.0/24`) and saved the output as an XML file, which was then rendered as an HTML report using an XSL stylesheet. The scan was run with the `--privileged` flag for accurate results.

**Scan command:**
```
nmap --privileged -P -oX network_scan_report.xml xx1.202.189.0/24
```

**Scan duration:** ~152 seconds (Sat Apr 18 17:30:47 → 17:33:19)
**Total IPs probed:** 256
**Hosts found online:** 6

---

### Findings

#### Host: xx1.202.189.1
**Hostname:** `1.bd.caa1.ip4.static.sl-reverse.com`

Most ports were closed (995 closed, reset). A handful of notable ports were visible:

| Port | State    | Service        |
|------|----------|----------------|
| 25   | Filtered | SMTP           |
| 135  | Filtered | MSRPC          |
| 139  | Filtered | NetBIOS-SSN    |
| 161  | Open     | SNMP           |
| 445  | Filtered | Microsoft-DS   |

The presence of open SNMP (port 161) is worth flagging — SNMP with default community strings is a classic misconfiguration that can expose device information. The filtered Windows ports (135, 139, 445) suggest a firewall is blocking access to what might be a Windows machine.

---

#### Host: xx1.202.189.3
**Hostname:** `3.bd.caa1.ip4.static.sl-reverse.com`

All 1000 scanned ports returned `filtered` with no response. This host is alive (ping responded) but is either behind a strict firewall or a network appliance that drops unsolicited packets silently. No actionable port data available.

---

#### Host: xx1.202.189.4
**Hostname:** `firewall-parkwayhealth-sig01-p1.sl1590293.sl.edst.ibm.com`

All 1000 ports filtered, no response. The hostname itself is revealing — this is clearly a firewall device associated with IBM infrastructure. No open ports were found, which makes sense for a dedicated perimeter device.

---

#### Host: xx1.202.189.11
**Hostname:** `b.bd.caa1.ip4.static.sl-reverse.com`

All 1000 ports filtered. No open ports detected. Similar profile to .3 — alive but not exposing anything to external scans.

---

#### Host: xx1.202.189.12
**Hostname:** `c.bd.caa1.ip4.static.sl-reverse.com`

All 1000 ports filtered. Same pattern as the previous two hosts. This group of hosts (.3, .11, .12) appears to be heavily firewalled infrastructure, possibly backend servers with no intended external exposure.

---

#### Host: xx1.202.189.98
**Hostname:** `62.bd.caa1.ip4.static.sl-reverse.com`

This is the most interesting host on the subnet. It had 977 closed ports, 5 filtered, and a significant number of open ports:

| Port  | State | Service        | Notes                          |
|-------|-------|----------------|--------------------------------|
| 19    | Filtered | Chargen     | Old echo/test protocol         |
| 25    | Filtered | SMTP         | Mail port blocked              |
| 80    | Open  | HTTP           | Web server running             |
| 81    | Open  | HTTP alt       | Secondary web port             |
| 82    | Open  | HTTP alt       | Possibly multiple web services |
| 100   | Open  | —              | Unusual, non-standard          |
| 135   | Filtered | MSRPC       | Windows RPC, blocked           |
| 139   | Filtered | NetBIOS-SSN | SMB precursor, blocked         |
| 445   | Filtered | SMB          | File sharing, blocked          |
| 3306  | Open  | MySQL          | **Database exposed on network**|
| 3389  | Open  | RDP            | **Remote Desktop open**        |
| 5985  | Open  | WS-Management  | Windows Remote Management      |
| 7070  | Open  | RealServer     | Streaming or proxy service     |
| 8081  | Open  | HTTP alt       | Another web interface          |
| 49152–49163 | Open | Dynamic RPC | Windows high-range ports  |

---

### Analysis

The .98 host presents a notably large and varied attack surface. A few things stand out immediately:

**MySQL (3306) is publicly reachable.** Database ports should never be exposed directly to the internet or even to a broad internal scan range unless there is a specific architectural reason. If this is an internet-facing address, this is a serious concern. Default credentials and unpatched MySQL instances are a common initial access vector.

**RDP (3389) is open.** Remote Desktop Protocol being accessible from the network means anyone who can reach this host can attempt authentication. RDP has been the target of numerous critical vulnerabilities over the years, and brute-force or credential stuffing attacks against it are extremely common.

**WS-Management (5985)** being open means PowerShell remoting is likely enabled, which further extends remote code execution capability to anyone who authenticates.

**Multiple HTTP ports (80, 81, 82, 8081)** suggest this machine is running several web services simultaneously — possibly a Windows server acting as an application host. Each of these is a potential entry point if any of the applications have vulnerabilities.

The pattern of closed (not filtered) ports on .1 and .98 is different from the fully filtered hosts — these machines are probably not behind a stateful firewall and instead rely on the OS to reject connections. This makes them more directly fingerprint-able.

---

### Overall Summary

| Host         | Status  | Notable                         |
|--------------|---------|---------------------------------|
| .1           | Online  | SNMP open, Windows ports filtered |
| .3           | Online  | Fully firewalled                |
| .4 (IBM FW)  | Online  | Dedicated firewall, no ports    |
| .11          | Online  | Fully firewalled                |
| .12          | Online  | Fully firewalled                |
| .98          | Online  | High-risk: RDP, MySQL, HTTP x4  |

The subnet scan shows a mostly locked-down environment with one exception: host .98 is running a wide range of services and deserves further investigation. In a real penetration test or security audit, this would be the first host to enumerate in depth.


