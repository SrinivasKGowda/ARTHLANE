# Arthlane

A Nifty F&O market terminal: live boards, paper trades, a trade journal, and account sign-in.

## What is in this repo

| Folder | Role |
| --- | --- |
| `market-oracle/` | The web app (`index.html`) and its Python server |
| `arthlane-backend/` | Java 21 / Spring Boot accounts, OTP, 2FA, profile, paper trades, journal |
| `deploy/` | Docker Compose, Caddy HTTPS, and the server guide |

## Run on your PC

You need Java 21, Maven (or the included `mvnw`), and Python 3.

```powershell
# Terminal 1 — accounts API, http://127.0.0.1:8766
cd arthlane-backend
.\mvnw.cmd spring-boot:run

# Terminal 2 — site, http://127.0.0.1:8765
cd market-oracle
python server.py
```

Open `http://127.0.0.1:8765`. In this mode, sign-in codes are printed in the backend console (and shown on the page) so you do not need email.

## Put it on the internet

See [deploy/README.md](deploy/README.md). For a free Oracle Cloud server, see [deploy/ORACLE.md](deploy/ORACLE.md).
