# Deployment Context

## Development Model

Development happens **locally on Mac** using Cursor and OpenSpec.

Do **not** assume development happens directly on the Linux server. The server runs deployed artifacts; the Mac is the authoring and implementation environment.

## Deployment Model

Deployment happens later as a **Docker container** on the Linux server. The container mounts a host folder that is also visible from the Mac via a shared network folder.

## Server Details

| Item | Value |
|------|-------|
| Server IP | `192.168.0.194` |
| Host folder | `/home/silverman/compartido_mac/silverman-blog-linkedin` |
| Mac shared folder name | `Compartido_Mac` |
| Container mount path | `/data/silverman-blog-linkedin` |

The same editorial directory tree (`blog-posts/`, `linkedin-posts/`, `metadata/`, `prompts/`) lives under the host path. The container sees it at `/data/silverman-blog-linkedin`. Local development may use a clone of this tree or a local mirror configured via environment variables.

## n8n and Server Relationship

- n8n runs on the Linux server (`192.168.0.194`).
- n8n workflows call the worker over HTTP (same host or Docker network, depending on final compose layout).
- n8n does **not** execute shell commands against the worker codebase via Execute Command.
- Editorial files may be placed manually on the Mac into the shared folder; n8n triggers processing when files appear or on a schedule.

## Local vs Container

| Concern | Local (Mac) | Server (Docker) |
|---------|-------------|-----------------|
| Code changes | Yes | Deploy updated image |
| OpenSpec / Cursor | Yes | No |
| Editorial file placement | Via shared folder | Same files via mount |
| n8n workflow editing | Browser to server n8n | n8n on server |
| Worker HTTP calls | Local worker or tunneled URL for dev | Container HTTP port |

## Operational Notes

- Secrets (API keys) belong in environment configuration on the server, not in the repository.
- Dockerfile and compose definitions will be created through future OpenSpec changes, not during context bootstrap.
- Phase 1 does not require production deployment until the foundation and process-ready changes are implemented and tested locally.
