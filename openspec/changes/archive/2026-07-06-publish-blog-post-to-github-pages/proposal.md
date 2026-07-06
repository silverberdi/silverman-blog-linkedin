## Why

The editorial pipeline already generates LinkedIn drafts from internal blog posts in `blog-posts/ready/`, but there is no safe bridge to publish those posts to the public Jekyll/GitHub Pages blog at [silverman.pro](https://silverman.pro) (backed by [silverberdi/silverberdi.github.io](https://github.com/silverberdi/silverberdi.github.io)). Operators currently must manually copy Markdown, rename files with date prefixes, place images under `assets/images/`, and normalize Jekyll frontmatter—error-prone steps that break naming conventions and risk overwriting existing public posts.

This change introduces a small, dry-run-first publishing helper that prepares one ready editorial post pair (`<slug>.md` + `<slug>.png`) into a local checkout of the public blog repository, reporting the expected canonical URL. It is the MVP for Phase 5 (GitHub Blog Publishing) in the backlog: turn internal editorial content into public blog assets without automatic git push, LinkedIn publish, or moving sources out of `ready/`.

## Goals

- Provide a version-controlled publishing helper that copies/prepares one ready blog post pair from the internal editorial workspace into a local checkout of `silverberdi.github.io`.
- Default to dry-run (or require an explicit `--apply` flag) so operators can preview outputs before writing files.
- Validate source Markdown exists, matching PNG exists, and source slug is safe for URL/path use.
- Derive public slug from source slug (strip leading numeric ordering prefix by default) or accept `--public-slug` override; validate public slug safety.
- Generate Jekyll post filename `YYYY-MM-DD-<public-slug>.md` using current date or an explicitly provided publication date.
- Copy PNG to `assets/images/<public-slug>.png` and set frontmatter `image: /assets/images/<public-slug>.png`.
- Normalize or write Jekyll frontmatter (`layout`, `title`, `date`, `categories`, `tags`, `description`, `image`) while preserving body content.
- Report the expected public URL as `https://silverman.pro/YYYY/MM/DD/<public-slug>/`.
- Refuse to overwrite existing public post files or images unless a future explicit option is designed.
- Leave source files in `blog-posts/ready/` unchanged.
- Include automated tests for filename transformation, image path convention, public URL generation, and non-overwrite behavior.

## Non-Goals

- Automatic `git push` to GitHub or GitHub Pages deployment.
- LinkedIn publishing or draft generation.
- ComfyUI image generation.
- Moving source posts from `blog-posts/ready/` to `processed/` or `error/`.
- Overwriting existing `_posts/` entries or `assets/images/` files in the public repo.
- A new HTTP worker endpoint (MVP is an operator-run helper under `deploy/server` or equivalent).
- n8n workflow integration or Execute Command nodes.
- Batch publishing of multiple posts in one invocation.
- Dairector content paths.

## What Changes

- Add a new `github-pages-blog-publishing` capability: a CLI publishing helper (Python module + thin shell wrapper) invoked by the operator on the Ubuntu server or locally during development.
- Add configuration for editorial base path, public blog repo checkout path, canonical site URL (`https://silverman.pro`), and dry-run vs apply mode.
- Implement source slug and public slug validation, source pair validation, public slug derivation, Jekyll filename generation, frontmatter normalization, image copy, and public URL calculation.
- Implement safe non-overwrite checks for target `_posts/YYYY-MM-DD-<public-slug>.md` and `assets/images/<public-slug>.png`.
- Add documentation for the publication bridge (operator workflow, paths, dry-run/apply examples).
- Add unit tests covering transformations, URL generation, frontmatter output, and overwrite refusal.
- No changes to existing worker HTTP endpoints (`GET /health`, `POST /process-ready`, `POST /process-file`).

## Why a Controlled Helper Script (Not n8n Execute Command)

n8n Execute Command runs arbitrary shell on the server host, which increases attack surface and embeds file-copy logic in workflow JSON instead of version-controlled code. A dedicated publishing helper keeps path validation, Jekyll conventions, dry-run defaults, and non-overwrite rules in tested Python under this repository—invoked explicitly by the operator (or later wrapped by n8n HTTP if a future change adds an endpoint). The helper does not replace the HTTP worker for LinkedIn generation; it complements it as the editorial-to-public-blog bridge.

## Capabilities

### New Capabilities

- `github-pages-blog-publishing`: Operator-invoked publishing helper that validates a ready editorial post pair (`<source-slug>.md` + `<source-slug>.png`), derives or accepts a public slug for published assets, prepares Jekyll post and image assets in a local `silverberdi.github.io` checkout, normalizes frontmatter, calculates the public URL, defaults to dry-run, and refuses overwrites.

### Modified Capabilities

<!-- No existing spec requirements change. Worker endpoints and ready-folder processing remain unchanged. -->

## Impact

- **Repository**: New Python module(s) and shell wrapper under `deploy/server/` (or aligned project location), plus tests under `tests/`.
- **APIs**: No new HTTP endpoints; existing worker API unchanged.
- **Editorial data**: Reads from `blog-posts/ready/<source-slug>.md` and `<source-slug>.png`; does not move or modify source files. Writes only to configured public blog repo checkout when `--apply` is used.
- **Public blog repo**: When applied, adds `_posts/YYYY-MM-DD-<public-slug>.md` and `assets/images/<public-slug>.png` to local checkout of `silverberdi.github.io`; operator commits and pushes manually.
- **Server**: Runs on Ubuntu host where editorial workspace lives (`/home/silverman/compartido_mac/silverman-blog-linkedin`) with access to a local clone of `silverberdi.github.io`.
- **Dependencies**: No new external services; may reuse existing Python stack (PyYAML or similar for frontmatter if not already present).
- **Security**: Validate slugs and paths; never expose secrets; refuse path traversal outside configured roots.
