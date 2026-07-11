# Project Overview

> **Historical bootstrap** (2026-07-10) — Superseded by [CURRENT-STATE.md](../CURRENT-STATE.md) for current status and roadmap. Retained for rationale and audience context.

## Repository

**silverman-blog-linkedin**

## Purpose

This repository will contain a local HTTP worker service for the `silverman-blog-linkedin` content automation system. The worker reads Markdown blog posts and generates LinkedIn draft variants. n8n orchestrates the workflow by calling the worker over HTTP.

## Business Goal

Silverio Bernal is a Solutions Architect. The content automation system supports two related objectives:

**Short-term:** Use his blog and LinkedIn profile to attract recruiters and C-level executives for remote senior roles around USD 7k/month.

**Medium/long-term:** Become recognized as a reference in AI, software architecture, digital transformation, agility, governance, and technology efficiency.

## Audience

- Recruiters sourcing senior remote roles
- C-level executives evaluating technical leadership and architecture capability
- Engineering leaders and peers interested in practical architecture and delivery discipline

Primary language is **English** because the target compensation is more likely outside LATAM.

## Why This Project Exists

n8n is already running on a Linux server and is the natural orchestration layer for content workflows. However, enabling n8n Execute Command increases operational risk on the server. Instead of running arbitrary shell commands from n8n, this project introduces a small, explicit HTTP worker that performs controlled file and content processing.

The worker keeps orchestration (n8n) separate from execution (file I/O, content generation, folder moves, metadata writes). That separation improves safety, testability, and clarity of responsibilities.

## Why Blog and LinkedIn Matter

- **Blog posts** are long-form, durable assets that demonstrate depth, architecture thinking, and business alignment. They serve as the canonical source of truth for ideas.
- **LinkedIn posts** are distribution assets derived from the blog. They reach recruiters and executives where they already spend attention, with formats tuned for engagement without duplicating the full editorial burden of writing from scratch each time.

Together, blog + LinkedIn create a pipeline: invest once in a strong article, generate multiple audience-specific LinkedIn variants, review and publish selectively.

## Phase 1 Scope

The first operational capability:

| Step | Behavior |
|------|----------|
| Input | Markdown blog posts placed manually in `blog-posts/ready/` |
| Processing | Generate LinkedIn draft variants from each blog post |
| Output | LinkedIn drafts written to `linkedin-posts/review/` |
| Metadata | Run and campaign metadata written to `metadata/runs/` and `metadata/campaigns/` |
| Success path | Processed source files move to `blog-posts/processed/` |
| Failure path | Failed source files move to `blog-posts/error/` |

## Explicitly Out of Scope (Phase 1)

- Dairector content
- Automatic LinkedIn publishing
- GitHub blog publishing
- n8n Execute Command
- Application code implementation (until an approved OpenSpec change authorizes it)

Future phases may add publishing, additional content sources, and richer n8n workflows. **Current roadmap:** [CURRENT-STATE.md](../CURRENT-STATE.md).
