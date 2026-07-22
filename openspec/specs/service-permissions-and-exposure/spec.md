# service-permissions-and-exposure

## Purpose

Operator-visible normative service permissions and exposure review for **BL-026 / US-062 + US-063**: least privilege, open ports, authentication, allowed paths, secrets separation (ratifying US-058), and documented accepted exposure (LAN-first worker/n8n/console; exceptional LinkedIn OAuth callback via Cloudflare for reauth only; Comfy Cloud and DeepSeek as outbound API clients; Google identity/allowlist on the separated LAN UI under BL-035 / US-097) — without public Authority Manager exposure (US-099), full US-098 JWT cutover, LinkedIn enablement mutation, or a network-security platform.

Operator procedure: `docs/operations/service-permissions-and-exposure.md`.

## Requirements

### Requirement: Normative exposure review artifact

The system documentation SHALL publish an operator-facing normative service permissions and exposure procedure at `docs/operations/service-permissions-and-exposure.md` identifying **BL-026 / US-062 and US-063**, including an **accepted exposure** inventory that states: worker API, n8n, and Authority Manager are LAN-only for current operations unless a later approved change (US-099) activates front-only public UI exposure; LinkedIn OAuth callback via public Cloudflare hostname is an **accepted exception** solely for LinkedIn reauthorization; Comfy Cloud and DeepSeek are outbound API clients (no inbound ComfyUI port on the worker host required); Google authentication identity/allowlist on the separated LAN UI is activated under **BL-035 / US-097** and operator JWT/session console→API auth under **US-098**, while **public** console exposure remains deferred to US-099; secrets separation is ratified from US-058. Publishing the procedure alone MUST NOT expose new public surfaces or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Accepted exposure inventory is explicit

- **WHEN** a system owner opens the normative exposure procedure
- **THEN** the document exists at `docs/operations/service-permissions-and-exposure.md`
- **AND** it lists accepted LAN-only surfaces and the OAuth callback exception
- **AND** it states that Google identity/allowlist (US-097) and operator JWT/session console auth (US-098) may be active on the LAN UI while public console exposure remains out of scope until US-099

### Requirement: Least privilege, ports, and authentication (US-062)

Normative docs SHALL provide a least-privilege and exposure checklist covering open/listening ports relevant to silverman-blog-linkedin operations, authentication expectations (worker API key for machine/n8n clients on non-callback routes; operator JWT/session for Google console path when US-098 is active; n8n on LAN), and fail-closed vocabulary (`blocked` / `confirmed clean` / `finding — remediation required`) without printing secrets. A live operator review on the deployment host MUST be supported by the procedure (Story accepted remains an operator gate after the live review or blocked recording).

#### Scenario: Ports and auth checklist defined

- **WHEN** an operator follows the US-062 checklist
- **THEN** listening ports and auth expectations for worker and n8n are listed
- **AND** outcomes use blocked/clean/finding vocabulary without secret values

#### Scenario: Auth checklist distinguishes console JWT from machine API key

- **WHEN** an operator reads authentication expectations after US-098
- **THEN** the checklist distinguishes n8n/machine API-key auth from Google console operator JWT/session auth and does not instruct placing the worker API key in the browser on the Google path

### Requirement: Allowed paths, secrets separation, and accepted exposure (US-063)

Normative docs SHALL inventory allowed filesystem mounts/paths (editorial data, public blog checkout, secrets mounts, deploy artifacts), ratify secrets separation per US-058 (server-local `.env` and secrets directory classes — never commit real values), and document the accepted exposure table as the shared meaning of “exposed only as required.” Findings MUST record path classes and port/service names only.

#### Scenario: Paths and secrets separation documented

- **WHEN** an operator follows the US-063 sections
- **THEN** allowed path/mount classes are named
- **AND** secrets separation is ratified without duplicating the full US-058 checklist
- **AND** accepted exposure is documented as operator policy

### Requirement: Visibility and independence

Normative docs SHALL update CURRENT-STATE / GLOSSARY / light product pointers after apply when exposure language changes. The procedure MUST NOT require making Authority Manager internet-public (US-099), MUST NOT require Flow A/B behavior changes, and MUST NOT mutate LinkedIn publication enablement. Thin cross-links from US-058 MAY note BL-026 as the broader exposure review. Cross-links MAY note BL-035 for Google console identity (US-097) and operator JWT console→API (US-098).

#### Scenario: Procedure does not expose console publicly

- **WHEN** an operator completes the published BL-026 procedure after US-098 docs alignment
- **THEN** it does not instruct making Authority Manager internet-public (that remains US-099)
- **AND** it does not instruct changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
- **AND** it may reference Google LAN identity/allowlist (US-097) and operator JWT/session console auth (US-098) without treating public tunnel exposure as accepted
