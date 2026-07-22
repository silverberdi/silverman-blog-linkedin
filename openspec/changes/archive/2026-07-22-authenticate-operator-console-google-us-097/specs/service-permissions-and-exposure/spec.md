## MODIFIED Requirements

### Requirement: Normative exposure review artifact

The system documentation SHALL publish an operator-facing normative service permissions and exposure procedure at `docs/operations/service-permissions-and-exposure.md` identifying **BL-026 / US-062 and US-063**, including an **accepted exposure** inventory that states: worker API, n8n, and Authority Manager are LAN-only for current operations unless a later approved change (US-099) activates front-only public UI exposure; LinkedIn OAuth callback via public Cloudflare hostname is an **accepted exception** solely for LinkedIn reauthorization; Comfy Cloud and DeepSeek are outbound API clients (no inbound ComfyUI port on the worker host required); Google authentication identity/allowlist on the separated LAN UI is activated under **BL-035 / US-097** while **public** console exposure remains deferred to US-099; secrets separation is ratified from US-058. Publishing the procedure alone MUST NOT expose new public surfaces or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Accepted exposure inventory is explicit

- **WHEN** a system owner opens the normative exposure procedure
- **THEN** the document exists at `docs/operations/service-permissions-and-exposure.md`
- **AND** it lists accepted LAN-only surfaces and the OAuth callback exception
- **AND** it states that Google identity/allowlist (US-097) may be active on the LAN UI while public console exposure remains out of scope until US-099

### Requirement: Visibility and independence

Normative docs SHALL update CURRENT-STATE / GLOSSARY / light product pointers after apply when exposure language changes. The procedure MUST NOT require making Authority Manager internet-public (US-099), MUST NOT require full US-098 JWT cutover, MUST NOT require Flow A/B behavior changes, and MUST NOT mutate LinkedIn publication enablement. Thin cross-links from US-058 MAY note BL-026 as the broader exposure review. Cross-links MAY note BL-035 for Google console identity activation.

#### Scenario: Procedure does not expose console publicly

- **WHEN** an operator completes the published BL-026 procedure after US-097 docs alignment
- **THEN** it does not instruct making Authority Manager internet-public (that remains US-099)
- **AND** it does not instruct changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
- **AND** it may reference Google LAN identity/allowlist (US-097) without treating public tunnel exposure as accepted
