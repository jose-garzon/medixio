# 04 — Deploy to Home Server & Verify Health

> **Goal:** ship the current image to your home server, run it under `docker compose`, and curl `/health` from somewhere outside the server. Establish the CI → registry → server pull pipeline once, then reuse it for every later step.

---

## Why this step exists

Deploy is the longest-tail source of "works on my laptop" bugs. Doing it while the app is trivial (one route, no DB writes) means every later iteration is a known-safe `git pull` + image refresh, not a fresh deploy adventure.

You'll learn:

- How GitHub Actions builds and pushes a multi-arch image to GHCR.
- How a private registry pull is authenticated on a Linux box.
- Two patterns for "new image is available → restart container": Watchtower vs cron pull script.
- Why you should never expose the bot's port to the public internet without something in front.

## Prerequisites

- Steps 01–03 done; locally `curl :8000/health` returns ok.
- A home server reachable via SSH.
- Docker + `docker compose` plugin installed on the server.
- Repo pushed to GitHub.

## Concepts

**GHCR.** GitHub's container registry, accessed at `ghcr.io/<owner>/<repo>`. Free for both public and private images. Auth via a Personal Access Token (PAT) with `read:packages` (for pull) and `write:packages` (for push from CI).

**Tag strategy.** Two tags per build: `latest` (mutable, "newest main") and `${{ github.sha }}` (immutable, exact commit). Deploys roll forward by pulling `latest`; rollback uses the SHA tag.

**Watchtower.** A container that periodically checks all running containers for new image digests and `docker compose up`-recreates them. Zero touch but a black box; misbehaves get tricky to debug.

**Cron pull script.** A shell script on the server that runs `docker compose pull && docker compose up -d`. Five lines, transparent, runs from `cron` or `systemd`. Recommended unless you're managing many services.

## Steps

### 1. GitHub Actions workflow

`.github/workflows/build-and-push.yml`:

```yaml
name: build-and-push

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}   # owner/repo

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3

      - name: Lint + test
        run: |
          uv sync --frozen
          uv run ruff check .
          uv run pytest -q

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=latest,enable={{is_default_branch}}
            type=sha,format=short

      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Push and verify the workflow runs green. Confirm an image appears under your repo's "Packages" tab.

### 2. Make the image pullable from the server

On GitHub: **Profile → Settings → Developer settings → Personal access tokens → Tokens (classic)** → generate one with `read:packages`. Note the value; you'll discard it after the next step.

On the home server:

```bash
echo "$PAT" | docker login ghcr.io -u <your-github-username> --password-stdin
```

Credentials cache to `~/.docker/config.json`. From now on `docker pull` works.

### 3. Prepare the server directory

```bash
mkdir -p ~/medixio && cd ~/medixio
# Copy these two files from the repo
scp docker-compose.yml home-server:~/medixio/
scp .env.example home-server:~/medixio/.env
$EDITOR .env        # set real POSTGRES_PASSWORD, etc.
```

Edit `docker-compose.yml` on the server: replace `build: .` with `image: ghcr.io/<owner>/medixio:latest`. Now the server doesn't need the source code, only the compose file and `.env`.

```yaml
  bot:
    image: ghcr.io/<owner>/medixio:latest
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"
    healthcheck: { ... same as step 03 ... }
    restart: unless-stopped
```

### 4. First deploy

```bash
docker compose pull
docker compose up -d
docker compose ps              # both Up (healthy)
docker compose logs -f bot
```

### 5. Curl from outside

From your laptop, on the same LAN as the server:

```bash
curl http://<home-server-ip>:8000/health
# {"status":"ok"}
```

If you want it reachable from the wider internet, **don't** open port 8000 to the world. Two safer paths:

- **Tailscale.** Install on server + laptop, hit `http://<server-tailnet-name>:8000/health`.
- **Reverse proxy** (Caddy / Traefik / nginx) terminating TLS with Let's Encrypt, with HTTP auth in front. Out of scope for this step.

### 6. Pick an update pattern

**Option A — cron pull script (recommended).**

`~/medixio/update.sh`:

```sh
#!/bin/sh
set -e
cd ~/medixio
docker compose pull
docker compose up -d
docker image prune -f
```

```bash
chmod +x ~/medixio/update.sh
crontab -e
# every 5 minutes:
*/5 * * * * /home/<user>/medixio/update.sh >> /home/<user>/medixio/update.log 2>&1
```

**Option B — Watchtower.**

Append to `docker-compose.yml`:

```yaml
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 300 --cleanup
    restart: unless-stopped
```

Pick one, not both.

### 7. End-to-end test

On your laptop:

```bash
# Make a trivial change to /health response
git commit -am "test deploy: tweak health payload"
git push origin main
```

Wait for Actions to go green, then for your update mechanism to fire (5 min cron or Watchtower poll). Re-curl `/health` on the server — payload should reflect your change.

Revert the test change.

### 8. Commit CI

```bash
git add .github/workflows/build-and-push.yml
git commit -m "ci: build image on main and push to ghcr"
git push
```

## Files touched in this step

| Path | Purpose |
|---|---|
| `.github/workflows/build-and-push.yml` | CI image build + push |
| Server `~/medixio/docker-compose.yml` | uses GHCR image instead of `build:` |
| Server `~/medixio/.env` | real prod env |
| Server `~/medixio/update.sh` (Option A) | pull + recreate |

## Verification

- [ ] Actions workflow green on `push` to `main`.
- [ ] Image visible at `ghcr.io/<owner>/medixio:latest`.
- [ ] `docker compose ps` on server shows `bot` and `db` healthy.
- [ ] `curl http://<server>:8000/health` from your laptop returns `{"status":"ok"}`.
- [ ] Trivial change to `/health` deploys end-to-end within one update cycle.

## Common gotchas

- **`denied: permission_denied` on push** — workflow needs `permissions: packages: write`. Without it, `GITHUB_TOKEN` can't push to GHCR.
- **`unauthorized` on pull from server** — you logged in as the wrong user, or your PAT lacks `read:packages`. Re-run `docker login` with the right PAT.
- **`exec format error` on the server** — your local build was `arm64`, server is `amd64`. CI builds for `linux/amd64` by default; if your server is different, add `platforms: linux/amd64,linux/arm64` to `build-push-action`.
- **Update never picks up new image** — Watchtower only triggers on changed *digest*, not just a re-pushed tag with the same digest. Make sure CI actually rebuilt (each push to main does).
- **Public exposure surprise** — UPnP / router config sometimes auto-forwards. Verify with `nmap -p 8000 <public-ip>` from a phone on cellular.
