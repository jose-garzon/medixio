# Medixio

WhatsApp assistant that helps patients in Colombia keep up with the paperwork of a
chronic illness: appointments, fórmulas médicas, EPS authorizations, monthly pharmacy
pickups, pendientes, PQRS and tutelas.

> **Disclaimers**
> - Medixio gives **no medical or legal advice**. PQRS/tutela help is general
>   information; rules in `src/medixio/knowledge/` must be reviewed before use.
> - WhatsApp access uses [neonize](https://github.com/krypton-byte/neonize), an
>   **unofficial** client. It may break WhatsApp's Terms of Service and the bot's
>   number can be banned. Use a dedicated number and low message volumes.
> - If you self-host it you are responsible for the health data you store
>   (in Colombia: Ley 1581 de 2012, datos sensibles).

- Why and what: [docs/intent.md](docs/intent.md)
- How: [docs/design.md](docs/design.md)

## Quick start (local, without WhatsApp)

```bash
cp .env.example .env          # set ANTHROPIC_API_KEY
uv sync
just migrate
just dev                      # API on :8000, WhatsApp disabled
just chat "hola"              # talk to the bot as a fake number
```

## Run with WhatsApp

```bash
just run                      # or: just up (Docker)
just logs                     # scan the QR with the bot's phone (WhatsApp > Linked devices)
```

The session is kept in `data/wa_session/`. The SQLite DB lives in `data/medixio.db`.

## Admin

- `GET /health` — DB and WhatsApp status.
- `POST /admin/chat` — talk to the bot as any JID.
- `GET /admin/knowledge/unreviewed` — rules and guides waiting for your review.
  Review = verify source, set `reviewed_on: YYYY-MM-DD` in
  `src/medixio/knowledge/defaults.yaml` or the guide front-matter.
- `POST /admin/reminders/dispatch` — run a scheduler tick now.
- `GET /admin/obs` — status dashboard: health checks, metrics, recent errors.
  JSON at `/admin/obs/status`, `/admin/obs/metrics`, `/admin/obs/events`.
  Data in `data/observability.db` (30-day retention).

Set `ADMIN_TOKEN` to require an `x-admin-token` header. It's mandatory (16+ chars)
when the API isn't bound to localhost, including Docker: `openssl rand -hex 24`.

Rate limits (per number, images, sign-ups, daily token budget) are configured in
`.env`; see `docs/design.md` §10.2. Blocked numbers: `/admin/obs/ratelimits`.

## Development

```bash
just check    # ruff + mypy strict
just test     # pytest + coverage
just migration "describe change"
```

## License

[MIT](LICENSE)
