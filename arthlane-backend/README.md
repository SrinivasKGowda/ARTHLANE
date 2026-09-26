# Arthlane backend

Accounts, OTP sign-in, authenticator-app two-factor codes, trader profiles, paper positions and the trade journal for the Arthlane web app. Java 21, Spring Boot 4, PostgreSQL (H2 file database for local development).

## Run locally

```powershell
.\mvnw.cmd spring-boot:run
```

The API listens on `http://127.0.0.1:8766` (set `PORT` to change it) and keeps its data in `./data/`. In development, sign-in codes are printed in the console and returned as `devCode` so you can sign in without an SMS provider.

Run the tests with `.\mvnw.cmd test`.

## API

All endpoints are under `/api/v1`. Everything except `/auth/*` needs `Authorization: Bearer <accessToken>`. Errors are returned as RFC 9457 problem details with a readable `detail`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/otp/request` | Send a 6-digit code to an email or Indian mobile |
| POST | `/auth/otp/verify` | Exchange the code for tokens (or a two-factor step) |
| POST | `/auth/2fa/verify` | Finish sign-in with an authenticator code |
| POST | `/auth/refresh` | Swap a refresh token for new tokens (single use) |
| POST | `/auth/logout` | End this session |
| GET, PUT | `/me` | Read or update the profile |
| POST | `/me/security/2fa/setup`, `/enable`, `/disable` | Manage authenticator-app sign-in |
| POST | `/me/security/logout-all` | End every session |
| GET, POST | `/positions` | List or open paper positions (idempotent by `clientRef`) |
| POST | `/positions/{id}/close` | Close at an exit price; the server records P&L in the journal |
| DELETE | `/positions/{id}` | Remove a position without recording it |
| GET, POST | `/journal` | List or import closed trades |
| DELETE | `/journal/{id}` | Delete a journal entry |
| GET | `/journal/stats` | Win rate, averages, best and worst trade, profit factor |

## Security model

- Sign-in codes are stored as HMAC hashes, expire after 5 minutes, allow 5 wrong tries, a 30-second resend gap, 5 codes per hour per address and 20 per hour per network (IP) address.
- Access tokens are 15-minute HS256 JWTs. Refresh tokens are random, stored hashed, and rotate on every use; reusing an old one signs out every session of that account.
- Two-factor codes follow RFC 6238, are accepted once each, and lock for 5 minutes after 5 wrong codes.
- CORS only allows the web app's origin.

## Production

`../deploy/` runs the whole site (this API, the web app, PostgreSQL and HTTPS) with Docker Compose; its README is the step-by-step server guide. To run this API on its own instead, use the `prod` profile (the Docker image does this) with these environment variables:

| Variable | Value |
| --- | --- |
| `DATABASE_URL`, `DATABASE_USER`, `DATABASE_PASSWORD` | PostgreSQL connection, for example `jdbc:postgresql://localhost:5432/arthlane` |
| `ARTHLANE_JWT_SECRET` | At least 32 random bytes (`openssl rand -base64 48`) |
| `ARTHLANE_CORS_ORIGINS` | The site's https origin, for example `https://arthlane.in` |
| `SPRING_MAIL_HOST`, `SPRING_MAIL_PORT`, `SPRING_MAIL_USERNAME`, `SPRING_MAIL_PASSWORD` | SMTP account that emails sign-in codes (STARTTLS on port 587) |
| `ARTHLANE_MAIL_FROM` | Sender shown on the email, for example `Arthlane <no-reply@arthlane.in>` |

In production, codes are only ever delivered by email: `devCode` is never returned, and signing in with a mobile number answers "not available yet" until an SMS sender exists. To add one, implement `OtpSender` for phone numbers (Indian SMS needs DLT registration of the sender ID and message template); the first sender whose `supports()` accepts an address is used.

Still to do before a large launch:

1. Move the refresh token from browser storage into an `httpOnly`, `Secure`, `SameSite=Strict` cookie.
2. The two-factor lockout and per-IP code counters are in memory; use Redis or the database once you run more than one API server.
3. Add a privacy notice, consent and account-deletion flow for the Digital Personal Data Protection Act, 2023.
