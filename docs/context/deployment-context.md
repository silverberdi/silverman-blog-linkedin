# Deployment Context

Canonical status: [CURRENT-STATE.md](../CURRENT-STATE.md). Live flags: [RUNTIME-STATE.md](../RUNTIME-STATE.md). Deploy guide: [ubuntu-server-worker-deployment.md](../deployment/ubuntu-server-worker-deployment.md).

## Development Model

Development happens **locally on Mac** using Cursor and OpenSpec.

Do **not** assume development happens directly on the Linux server. The server runs deployed artifacts; the Mac is the authoring and implementation environment.

## Deployment Model

Production worker runs as a **Docker container** on the Linux server. The container mounts host folders for editorial data and the public GitHub Pages checkout.

## Server Details

| Item | Value |
|------|-------|
| Server IP | `192.168.0.194` |
| Worker port | `8010` |
| Editorial host folder | `/home/silverman/compartido_mac/silverman-blog-linkedin` |
| Container editorial mount | `/data/silverman-blog-linkedin` |
| Public blog host folder | `/home/silverman/silverberdi.github.io` |
| Container public mount | `/public-blog` |
| Mac shared folder name | `Compartido_Mac` |

## n8n and Server Relationship

- n8n runs on the Linux server (`192.168.0.194`).
- n8n workflows call the worker over HTTP only — never Execute Command (ADR-0001).
- Flow A workflow is **imported but inactive** at last baseline — see RUNTIME-STATE.
- Editorial files may be placed on the Mac into the shared folder.

## Local vs Container

| Concern | Local (Mac) | Server (Docker) |
|---------|-------------|-----------------|
| Code changes | Yes | Deploy updated image (`BUILD_REVISION`) |
| OpenSpec / Cursor | Yes | No |
| Editorial file placement | Via shared folder | Same files via mount |
| n8n workflow editing | Browser to server n8n | n8n on server |
| Worker HTTP | `localhost:8000` dev | `192.168.0.194:8010` |

## Operational Notes

- Secrets belong in server `.env`, not the repository.
- Git commit/push for site published/live is **manual** after worker handoff.
- Deploy: `deploy/server/deploy-worker.sh` on the Ubuntu server.
