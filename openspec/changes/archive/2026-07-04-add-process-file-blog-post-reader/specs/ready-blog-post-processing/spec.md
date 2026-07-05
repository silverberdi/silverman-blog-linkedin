## MODIFIED Requirements

### Requirement: API key authentication for processing endpoints

The worker SHALL require valid API key authentication for processing endpoints (`POST /process-ready` and `POST /process-file`) using the configured `SILVERMAN_BLOG_LINKEDIN_API_KEY`.

The client MUST send the key in the `Authorization` header as a Bearer token: `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`.

#### Scenario: Valid API key for process-ready

- **WHEN** a client sends `POST /process-ready` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with folder validation and metadata directory readiness checks before any candidate scanning

#### Scenario: Valid API key for process-file

- **WHEN** a client sends `POST /process-file` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation, folder validation, and metadata directory readiness checks before reading the requested file

#### Scenario: Missing Authorization header

- **WHEN** a client sends `POST /process-ready` or `POST /process-file` without an `Authorization` header
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose secret values

#### Scenario: Invalid API key

- **WHEN** a client sends `POST /process-ready` or `POST /process-file` with an incorrect Bearer token
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose the expected key or configured secret

#### Scenario: Auth failure does not leak secrets

- **WHEN** authentication fails for `POST /process-ready` or `POST /process-file`
- **THEN** the response and logs MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or the submitted token value
