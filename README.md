
## Task 3 — SSH: Key Discovery Script

### What I Did

The goal here was to write a bash script that SSHs into a remote server, searches the entire filesystem for public/private key files, and pulls them back locally.

I used `sshpass` to handle the password-based authentication non-interactively, which is necessary when automating SSH from within a script. The remote commands are passed as a heredoc block so the server executes them all in one session.

### Script (`script.sh`)

```bash
#!/bin/bash

# Variables
pass="d33"
ip_addr="127.0.0.1"
user="d33"
local_output_file="found_keys.txt"

# Execute commands on the remote server
sshpass -p "$pass" ssh "$user"@"$ip_addr" << 'EOF'

search_dir="/"
output_file="found_keys.txt"

> "$output_file"

find "$search_dir" -type f \( -name "*.pem" -o -name "*.pub" -o -name "id_rsa*" -o -name "id_dsa*" \) >> "$output_file" 2>/dev/null

if [[ -s $output_file ]]; then
    echo "Keys found and saved to $output_file"
else
    echo "No keys found."
fi

cat "$output_file"
EOF

sshpass -p "$pass" scp "$user@$ip_addr:found_keys.txt" "$local_output_file"

if [[ -f $local_output_file ]]; then
    echo "Keys successfully uploaded to $local_output_file"
else
    echo "Failed to upload keys."
fi
```

### How It Works

The script connects to the target (`127.0.0.1` in this case, the local machine) as user `d33` using the password via `sshpass`. Once inside, it runs `find` starting from the root directory `/` and looks for files matching common SSH key naming patterns — `*.pem`, `*.pub`, `id_rsa*`, and `id_dsa*`. Errors from inaccessible directories are suppressed with `2>/dev/null` so the script doesn't get noisy.

After the search, the results file is copied back to the local machine using `scp`. The script ends by confirming whether the transfer succeeded.

### Notes

This script is kept simple and purposeful. In a real environment, the IP, username, and password would ideally be passed as arguments or pulled from a config rather than hardcoded. The `sshpass` approach works for scripting but isn't ideal for production — key-based auth is always preferable for automation.

---

## Task 9 — Hashing: Secure Password Storage & Verification

### What I Did

I built a full terminal-based password manager application in Python that lets users register, log in, and view existing accounts. All passwords are stored as salted SHA-256 hashes — never in plain text.

### Application (`tool.py`)

The application has four main components:

**Hashing Logic** — The `get_hash()` function takes a password and an optional salt. If no salt is provided, it generates a random 16-byte salt using `os.urandom()`, then hashes the password + salt combination using `hashlib.sha256`. Both the hash and the salt are returned and stored.

**Storage** — User credentials are kept in a `vault.json` file. Each entry stores the hash and the salt, but never the original password. Example from the live vault:

```json
{
    "d33": {
        "hash": "44fffc347d8045f7c76b1491019570b2625333d4b08541c0a1981fb10a46cdc4",
        "salt": "0ff9a9a634774c666277ae0ab6733439"
    }
}
```

**Registration** — When a user registers, their password is hashed with a fresh random salt. The hash and salt pair get written to the vault.

**Login / Verification** — At login, the stored salt for the given username is retrieved. The entered password is hashed again with that same salt, and the result is compared against the stored hash. If they match, access is granted.

### Why Salting Matters

Salting prevents two major attack vectors. First, it means two users with the same password will have different hashes, so a database breach doesn't immediately reveal duplicates. Second, it defeats precomputed rainbow table attacks, because the attacker would need a separate rainbow table for every unique salt.

### UI

The application uses the `rich` library for a styled terminal interface with a fancy ASCII banner, a menu table, and coloured prompts. It's fully functional and runs as a standalone CLI tool.

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

