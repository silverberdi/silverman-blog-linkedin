# service-permissions-and-exposure

## Purpose

Operator-visible normative service permissions and exposure review for **BL-026 / US-062 + US-063**: least privilege, open ports, authentication, allowed paths, secrets separation (ratifying US-058), and documented accepted exposure (LAN-first worker/n8n/console; exceptional LinkedIn OAuth callback via Cloudflare for reauth only; Comfy Cloud and DeepSeek as outbound API clients) — without public Authority Manager exposure, Google/OIDC activation, LinkedIn enablement mutation, or a network-security platform.

Operator procedure: `docs/operations/service-permissions-and-exposure.md`.

## Requirements

### Requirement: Normative exposure review artifact

The system documentation SHALL publish an operator-facing normative service permissions and exposure procedure at `docs/operations/service-permissions-and-exposure.md` identifying **BL-026 / US-062 and US-063**, including an **accepted exposure** inventory that states: worker API, n8n, and Authority Manager are LAN-only for current operations; LinkedIn OAuth callback via public Cloudflare hostname is an **accepted exception** solely for LinkedIn reauthorization; Comfy Cloud and DeepSeek are outbound API clients (no inbound ComfyUI port on the worker host required); public console and Google authentication remain future/out of scope; secrets separation is ratified from US-058. Publishing the procedure alone MUST NOT expose new public surfaces or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Accepted exposure inventory is explicit

- **WHEN** a system owner opens the normative exposure procedure
- **THEN** the document exists at `docs/operations/service-permissions-and-exposure.md`
- **AND** it lists accepted LAN-only surfaces and the OAuth callback exception
- **AND** it states console public exposure / Google auth are out of scope for this change

### Requirement: Least privilege, ports, and authentication (US-062)

Normative docs SHALL provide a least-privilege and exposure checklist covering open/listening ports relevant to silverman-blog-linkedin operations, authentication expectations (worker API key on non-callback routes; n8n on LAN), and fail-closed vocabulary (`blocked` / `confirmed clean` / `finding — remediation required`) without printing secrets. A live operator review on the deployment host MUST be supported by the procedure (Story accepted remains an operator gate after the live review or blocked recording).

#### Scenario: Ports and auth checklist defined

- **WHEN** an operator follows the US-062 checklist
- **THEN** listening ports and auth expectations for worker and n8n are listed
- **AND** outcomes use blocked/clean/finding vocabulary without secret values

### Requirement: Allowed paths, secrets separation, and accepted exposure (US-063)

Normative docs SHALL inventory allowed filesystem mounts/paths (editorial data, public blog checkout, secrets mounts, deploy artifacts), ratify secrets separation per US-058 (server-local `.env` and secrets directory classes — never commit real values), and document the accepted exposure table as the shared meaning of “exposed only as required.” Findings MUST record path classes and port/service names only.

#### Scenario: Paths and secrets separation documented

- **WHEN** an operator follows the US-063 sections
- **THEN** allowed path/mount classes are named
- **AND** secrets separation is ratified without duplicating the full US-058 checklist
- **AND** accepted exposure is documented as operator policy

### Requirement: Visibility and independence

Normative docs SHALL update CURRENT-STATE / GLOSSARY / light product pointers after apply. The procedure MUST NOT require public console exposure, Google/OIDC activation, Flow A/B behavior changes, or LinkedIn publication enablement mutation. Thin cross-links from US-058 MAY note BL-026 as the broader exposure review.

#### Scenario: Procedure does not expose console publicly

- **WHEN** an operator completes the published BL-026 procedure
- **THEN** it does not instruct making Authority Manager internet-public or enabling Google auth
- **AND** it does not instruct changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
