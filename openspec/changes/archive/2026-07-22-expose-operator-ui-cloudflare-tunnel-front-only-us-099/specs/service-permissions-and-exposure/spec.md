## MODIFIED Requirements

### Requirement: Normative exposure review artifact

The system documentation SHALL publish an operator-facing normative service permissions and exposure procedure at `docs/operations/service-permissions-and-exposure.md` identifying **BL-026 / US-062 and US-063**, including an **accepted exposure** inventory that states: worker API and n8n remain LAN-only for current operations; Authority Manager **public** exposure, when activated under **US-099**, is **front-only** (Cloudflare Tunnel or equivalent to the separated operator UI) with the worker API remaining private; LinkedIn OAuth callback via public Cloudflare hostname is an **accepted exception** solely for LinkedIn reauthorization; Comfy Cloud and DeepSeek are outbound API clients (no inbound ComfyUI port on the worker host required); Google authentication identity/allowlist (US-097) and operator JWT/session console→API auth (US-098) apply on LAN and on the public UI URL when US-099 is active; secrets separation is ratified from US-058. Publishing the procedure alone MUST NOT expose the worker API publicly or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Accepted exposure inventory is explicit

- **WHEN** a system owner opens the normative exposure procedure after US-099 docs alignment
- **THEN** the document exists at `docs/operations/service-permissions-and-exposure.md`
- **AND** it lists LAN-only worker API and n8n, the OAuth callback exception, and front-only public Authority Manager UI (when US-099 active) with private API
- **AND** it states that Google identity/allowlist (US-097) and operator JWT/session console auth (US-098) apply without requiring the worker API to be internet-public

### Requirement: Least privilege, ports, and authentication (US-062)

Normative docs SHALL provide a least-privilege and exposure checklist covering open/listening ports relevant to silverman-blog-linkedin operations, authentication expectations (worker API key for machine/n8n clients on non-callback routes; operator JWT/session for Google console path when US-098 is active; n8n on LAN; public UI via tunnel only when US-099 is active), and fail-closed vocabulary (`blocked` / `confirmed clean` / `finding — remediation required`) without printing secrets. A live operator review on the deployment host MUST be supported by the procedure (Story accepted remains an operator gate after the live review or blocked recording).

#### Scenario: Ports and auth checklist defined

- **WHEN** an operator follows the US-062 checklist
- **THEN** listening ports and auth expectations for worker and n8n are listed
- **AND** outcomes use blocked/clean/finding vocabulary without secret values

#### Scenario: Auth checklist distinguishes console JWT from machine API key

- **WHEN** an operator reads authentication expectations after US-098/US-099
- **THEN** the checklist distinguishes n8n/machine API-key auth from Google console operator JWT/session auth and does not instruct placing the worker API key in the browser on the Google path or publishing the worker API

### Requirement: Visibility and independence

Normative docs SHALL update CURRENT-STATE / GLOSSARY / light product pointers after apply when exposure language changes. The procedure MUST NOT require publishing the worker API on the public internet, MUST NOT require Flow A/B behavior changes, and MUST NOT mutate LinkedIn publication enablement. Thin cross-links from US-058 MAY note BL-026 as the broader exposure review. Cross-links MAY note BL-035 for Google console identity (US-097), operator JWT console→API (US-098), and front-only public UI (US-099).

#### Scenario: Procedure accepts front-only UI without public API

- **WHEN** an operator completes the published BL-026 procedure after US-099 docs alignment
- **THEN** it may treat Cloudflare Tunnel front-only Authority Manager UI as accepted under US-099
- **AND** it does not instruct publishing the worker API on the public internet
- **AND** it does not instruct changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
