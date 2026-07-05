## MODIFIED Requirements

### Requirement: API key authentication for processing endpoints

The worker SHALL require valid API key authentication for processing endpoints (`POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, and `POST /generate-linkedin-draft`) using the configured `SILVERMAN_BLOG_LINKEDIN_API_KEY`.

The client MUST send the key in the `Authorization` header as a Bearer token: `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`.

#### Scenario: Valid API key for process-ready

- **WHEN** a client sends `POST /process-ready` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with folder validation and metadata directory readiness checks before any candidate scanning

#### Scenario: Valid API key for process-file

- **WHEN** a client sends `POST /process-file` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation, folder validation, and metadata directory readiness checks before reading the requested file

#### Scenario: Valid API key for write-linkedin-draft

- **WHEN** a client sends `POST /write-linkedin-draft` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation and targeted directory readiness checks before writing a review draft

#### Scenario: Valid API key for generate-linkedin-draft

- **WHEN** a client sends `POST /generate-linkedin-draft` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation and pre-generation checks before calling DeepSeek or writing a draft

#### Scenario: Missing Authorization header

- **WHEN** a client sends `POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, or `POST /generate-linkedin-draft` without an `Authorization` header
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose secret values

#### Scenario: Invalid API key

- **WHEN** a client sends `POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, or `POST /generate-linkedin-draft` with an incorrect Bearer token
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose the expected key or configured secret

#### Scenario: Auth failure does not leak secrets

- **WHEN** authentication fails for `POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, or `POST /generate-linkedin-draft`
- **THEN** the response and logs MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or the submitted token value
