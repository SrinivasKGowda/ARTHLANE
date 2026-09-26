# Putting Arthlane online at arthlane.in

This folder runs the whole site on one Linux server with Docker Compose:

| Service | What it does |
| --- | --- |
| `caddy` | Public web server. Gets and renews free HTTPS certificates from Let's Encrypt automatically, sends `/api/v1/*` to the API and everything else to the web app, and redirects `www` to the main address. |
| `web` | The Arthlane page and its market data (`market-oracle/`). |
| `api` | Accounts, sign-in, profiles, paper trades and journal (`arthlane-backend/`). |
| `db` | PostgreSQL, the database the API writes to. |

Only ports 80 and 443 are open to the internet. The API's health endpoint and the database are reachable only inside the server.

Rough running cost: the domain yearly, and a server at about ₹800–1,500 a month or free on Oracle Cloud. HTTPS certificates are free.

## 1. Rent a server

**Free option:** follow [ORACLE.md](ORACLE.md) instead of steps 1, 4 and 5.

Otherwise, any VPS with **Ubuntu 24.04**, **2 vCPU and 4 GB RAM** (2 GB works with the swap file in step 4), and a region close to your users: Mumbai, Bangalore or Singapore. DigitalOcean, AWS Lightsail, Linode/Akamai, Vultr and Hostinger all offer this. Note the server's public IP address.

## 2. Point the domain at the server

In your domain registrar's DNS settings for `arthlane.in`, add:

| Type | Name | Value |
| --- | --- | --- |
| A | `@` | your server IP |
| A | `www` | your server IP |

Check it from your PC after a few minutes: `nslookup arthlane.in` should print the server IP. Do this **before** step 7, because Let's Encrypt checks the domain points at your server before issuing the certificate.

## 3. Choose who sends the sign-in emails

Sign-in codes are emailed, so you need an SMTP account. A transactional email service is the easiest: Brevo, Amazon SES (Mumbai region), Resend, Postmark or Mailgun. Their free or cheap tiers cover a small site.

1. Sign up and add `arthlane.in` as a sending domain.
2. Add the DNS records they show you, usually SPF, DKIM and DMARC. Without them, codes land in spam.
3. Note the SMTP host, port (587), username and password.

Mobile-number sign-in stays off until an SMS provider is added. Indian SMS needs DLT registration first.

## 4. Prepare the server

From PowerShell on your PC:

```powershell
ssh root@YOUR_SERVER_IP
```

Then on the server:

```bash
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443
ufw enable

# Only needed on a 2 GB server, so the first build does not run out of memory
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 5. Copy the code to the server

From PowerShell on your PC, in `D:\SrinisStore (1)`. This leaves out build output and your local test database:

```powershell
tar -czf arthlane.tgz --exclude=target --exclude=data --exclude=__pycache__ --exclude=.env market-oracle arthlane-backend deploy
scp arthlane.tgz root@YOUR_SERVER_IP:/opt/
```

On the server:

```bash
mkdir -p /opt/arthlane && tar -xzf /opt/arthlane.tgz -C /opt/arthlane
```

(Pushing the project to a private Git repository and running `git clone` on the server works just as well.)

## 6. Fill in the settings

```bash
cd /opt/arthlane/deploy
cp .env.example .env
openssl rand -base64 48    # run twice: one value for POSTGRES_PASSWORD, one for ARTHLANE_JWT_SECRET
nano .env
```

Set `ACME_EMAIL` to your email, paste the two random values, and fill in the `MAIL_*` lines from step 3. Keep `.env` private: anyone with `ARTHLANE_JWT_SECRET` can sign in as any user. Save a copy in your password manager.

## 7. Start the site

```bash
docker compose up -d --build
```

The first build takes a few minutes. Then:

```bash
docker compose ps                  # all four services should be "running"; db shows "healthy"
docker compose logs -f caddy api   # Ctrl+C to stop watching
```

Open `https://arthlane.in`, go to your profile page and sign in with your email. The code should arrive within a minute.

## 8. Everyday tasks

**Update after changing the code:** copy the files again as in step 5 (the `.env` on the server is not overwritten), then:

```bash
cd /opt/arthlane/deploy && docker compose up -d --build
```

**Back up the database every night:**

```bash
mkdir -p /root/backups
crontab -e
```

Add this line:

```
0 2 * * * cd /opt/arthlane/deploy && docker compose exec -T db pg_dump -U arthlane arthlane | gzip > /root/backups/arthlane-$(date +\%F).sql.gz
```

Copy the backups off the server from time to time, for example with `scp root@YOUR_SERVER_IP:/root/backups/* .`. To restore one:

```bash
gunzip -c /root/backups/arthlane-2026-10-01.sql.gz | docker compose exec -T db psql -U arthlane arthlane
```

**Send arthlane.com to the same site:** add the same two A records for `arthlane.com`, uncomment the last block in `Caddyfile`, then run `docker compose restart caddy`.

## If something goes wrong

| Symptom | Where to look |
| --- | --- |
| Browser warns about the certificate | DNS not pointing at the server yet, or port 80 blocked: `docker compose logs caddy` |
| "We could not send your code just now" | SMTP host, port, username or password: `docker compose logs api` |
| "Sign-in codes cannot be sent right now" | `MAIL_HOST` is empty in `.env` |
| Build stops with "killed" | Not enough memory; add the swap file from step 4 |
| F&O chain or FII numbers blank | NSE often blocks requests from cloud servers; see the checklist below |

## Before you announce the site publicly

- **Market data licence.** The prices come from Yahoo Finance and NSE's website. That is fine for personal use, but a public site needs licensed data from an authorised vendor. NSE also frequently blocks cloud server addresses, so check the F&O pages right after going live.
- **SEBI.** Publishing buy/sell signals to the public can count as investment research, which needs SEBI Research Analyst registration. Until you have it, present signals as educational only with a clear disclaimer, and get a lawyer's view.
- **Privacy.** Under the Digital Personal Data Protection Act, 2023, you need a privacy notice, consent at sign-up and a way to delete an account.
- **Trademark.** File "Arthlane" in classes 9, 36 and 42 (about ₹4,500 per class online) before you spend on marketing.
