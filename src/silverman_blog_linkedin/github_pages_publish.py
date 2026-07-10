"""Operator CLI to prepare editorial blog posts for GitHub Pages / Jekyll."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from silverman_blog_linkedin.config import DEFAULT_BASE_PATH

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NUMERIC_PREFIX_PATTERN = re.compile(r"^\d+-(.+)$")
READY_RELATIVE = Path("blog-posts/ready")
POSTS_RELATIVE = Path("_posts")
IMAGES_RELATIVE = Path("assets/images")

ENV_BASE_PATH = "SILVERMAN_BLOG_LINKEDIN_BASE_PATH"
ENV_REPO_PATH = "SILVERMAN_GITHUB_PAGES_REPO_PATH"
ENV_SITE_URL = "SILVERMAN_SITE_URL"
DEFAULT_SITE_URL = "https://silverman.pro"
DEFAULT_LAYOUT = "post"
JEKYLL_DATE_SUFFIX = " 00:00:00 -0500"

BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED = "blog_image_public_asset_handoff_failed"


class PublishError(Exception):
    """Validation or publish conflict error with a user-facing message."""


@dataclass(frozen=True)
class PublishConfig:
    editorial_base: Path
    repo_path: Path
    site_url: str


@dataclass(frozen=True)
class PublishPlan:
    source_slug: str
    public_slug: str
    publication_date: date
    mode: str
    source_md: Path
    source_png: Path
    post_target: Path
    image_target: Path
    post_relative: str
    image_relative: str
    public_url: str
    status: str = "ready"


def validate_slug(slug: str, *, label: str = "slug") -> None:
    if not slug:
        raise PublishError(f"{label} is required")
    if not SLUG_PATTERN.match(slug):
        raise PublishError(
            f"unsafe {label} {slug!r}: must match ^[a-z0-9]+(?:-[a-z0-9]+)*$"
        )


def derive_public_slug(source_slug: str) -> str:
    match = NUMERIC_PREFIX_PATTERN.match(source_slug)
    if match:
        return match.group(1)
    return source_slug


def resolve_public_slug(
    source_slug: str, public_slug_override: str | None = None
) -> str:
    validate_slug(source_slug, label="source slug")
    if public_slug_override is not None:
        validate_slug(public_slug_override, label="public slug")
        return public_slug_override
    public_slug = derive_public_slug(source_slug)
    validate_slug(public_slug, label="public slug")
    return public_slug


def load_config(environ: dict[str, str]) -> PublishConfig:
    raw_base = environ.get(ENV_BASE_PATH, DEFAULT_BASE_PATH).strip()
    editorial_base = Path(raw_base).expanduser().resolve()

    raw_repo = environ.get(ENV_REPO_PATH, "").strip()
    if not raw_repo:
        raise PublishError(
            f"{ENV_REPO_PATH} is required and must point to the public blog repo checkout"
        )
    repo_path = Path(raw_repo).expanduser().resolve()

    site_url = environ.get(ENV_SITE_URL, DEFAULT_SITE_URL).strip().rstrip("/")
    if not site_url:
        raise PublishError(f"{ENV_SITE_URL} must not be empty")

    return PublishConfig(
        editorial_base=editorial_base,
        repo_path=repo_path,
        site_url=site_url,
    )


def parse_publication_date(raw: str | None) -> date:
    if raw is None:
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise PublishError(
            f"invalid publication date {raw!r}: expected YYYY-MM-DD"
        ) from exc


def _require_relative_to(path: Path, root: Path, label: str) -> None:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise PublishError(f"{label} escapes configured root: {path}")


def validate_repo_layout(repo_path: Path) -> None:
    if not repo_path.exists() or not repo_path.is_dir():
        raise PublishError(
            f"public blog repo checkout not found or not a directory: {repo_path}"
        )
    posts_dir = repo_path / POSTS_RELATIVE
    images_dir = repo_path / IMAGES_RELATIVE
    if not posts_dir.is_dir():
        raise PublishError(
            f"public blog repo missing _posts/ directory: {posts_dir}"
        )
    if not images_dir.is_dir():
        raise PublishError(
            f"public blog repo missing assets/images/ directory: {images_dir}"
        )


def resolve_source_paths(
    config: PublishConfig, source_slug: str
) -> tuple[Path, Path]:
    ready_dir = config.editorial_base / READY_RELATIVE
    if not ready_dir.is_dir():
        raise PublishError(
            f"editorial ready directory not found: {ready_dir}"
        )

    md_path = (ready_dir / f"{source_slug}.md").resolve()
    png_path = (ready_dir / f"{source_slug}.png").resolve()

    _require_relative_to(md_path, ready_dir, "markdown source path")
    _require_relative_to(png_path, ready_dir, "image source path")

    if not md_path.is_file():
        raise PublishError(
            f"missing markdown source: {READY_RELATIVE / f'{source_slug}.md'}"
        )
    if not png_path.is_file():
        raise PublishError(
            f"missing PNG source: {READY_RELATIVE / f'{source_slug}.png'}"
        )

    return md_path, png_path


def target_paths(
    config: PublishConfig, public_slug: str, publication_date: date
) -> tuple[Path, Path, str, str]:
    date_prefix = publication_date.isoformat()
    post_relative = f"{POSTS_RELATIVE / f'{date_prefix}-{public_slug}.md'}"
    image_relative = f"{IMAGES_RELATIVE / f'{public_slug}.png'}"

    post_target = (config.repo_path / post_relative).resolve()
    image_target = (config.repo_path / image_relative).resolve()

    _require_relative_to(post_target, config.repo_path, "post target path")
    _require_relative_to(image_target, config.repo_path, "image target path")

    return post_target, image_target, post_relative, image_relative


def public_url(site_url: str, publication_date: date, slug: str) -> str:
    return (
        f"{site_url.rstrip('/')}/"
        f"{publication_date.year:04d}/"
        f"{publication_date.month:02d}/"
        f"{publication_date.day:02d}/"
        f"{slug}/"
    )


def jekyll_date(publication_date: date) -> str:
    return f"{publication_date.isoformat()}{JEKYLL_DATE_SUFFIX}"


def _title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_yaml = parts[1]
    body = parts[2]
    if body.startswith("\n"):
        body = body[1:]
    elif body.startswith("\r\n"):
        body = body[2:]

    try:
        parsed = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        raise PublishError(f"invalid YAML frontmatter in source markdown: {exc}") from exc

    if not isinstance(parsed, dict):
        raise PublishError("source frontmatter must be a YAML mapping")

    return parsed, body


def _normalize_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _resolve_description(frontmatter: dict[str, Any]) -> str:
    description = frontmatter.get("description")
    if not _is_blank(description):
        return str(description).strip()
    subtitle = frontmatter.get("subtitle")
    if not _is_blank(subtitle):
        return str(subtitle).strip()
    return ""


def prepare_frontmatter(
    source_md: Path, public_slug: str, publication_date: date
) -> tuple[dict[str, Any], str]:
    content = source_md.read_text(encoding="utf-8")
    existing, body = _split_frontmatter(content)

    frontmatter: dict[str, Any] = dict(existing)
    frontmatter.pop("status", None)
    frontmatter["layout"] = frontmatter.get("layout") or DEFAULT_LAYOUT
    frontmatter["title"] = frontmatter.get("title") or _title_from_slug(public_slug)
    frontmatter["date"] = jekyll_date(publication_date)
    frontmatter["categories"] = _normalize_list(frontmatter.get("categories"))
    frontmatter["tags"] = _normalize_list(frontmatter.get("tags"))
    frontmatter["description"] = _resolve_description(frontmatter)
    frontmatter.pop("subtitle", None)
    frontmatter["image"] = f"/assets/images/{public_slug}.png"

    return frontmatter, body


def render_markdown(frontmatter: dict[str, Any], body: str) -> str:
    yaml_block = yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip()
    if body:
        return f"---\n{yaml_block}\n---\n{body}"
    return f"---\n{yaml_block}\n---\n"


def render_expected_public_post(
    source_md: Path, public_slug: str, publication_date: date
) -> str:
    """Return the canonical Jekyll post body that publish would write."""
    frontmatter, body = prepare_frontmatter(source_md, public_slug, publication_date)
    return render_markdown(frontmatter, body)


@dataclass(frozen=True)
class PublicBlogImageCopyResult:
    status: str
    image_relative: str
    error_message: str | None = None


def public_blog_image_relative(public_slug: str) -> str:
    """Return the public repo relative path for a blog hero image."""
    validate_slug(public_slug, label="public slug")
    return f"{IMAGES_RELATIVE / f'{public_slug}.png'}"


def copy_public_blog_image(
    source_png: Path,
    repo_path: Path,
    public_slug: str,
) -> PublicBlogImageCopyResult:
    """Copy a PNG into public assets/images when missing; reuse when target exists."""
    image_relative = public_blog_image_relative(public_slug)
    try:
        validate_repo_layout(repo_path)
    except PublishError as exc:
        return PublicBlogImageCopyResult(
            status="failed",
            image_relative=image_relative,
            error_message=str(exc),
        )

    image_target = (repo_path / image_relative).resolve()
    try:
        _require_relative_to(image_target, repo_path, "image target path")
    except PublishError as exc:
        return PublicBlogImageCopyResult(
            status="failed",
            image_relative=image_relative,
            error_message=str(exc),
        )

    if image_target.exists():
        if image_target.is_file():
            return PublicBlogImageCopyResult(
                status="reused",
                image_relative=image_relative,
            )
        return PublicBlogImageCopyResult(
            status="failed",
            image_relative=image_relative,
            error_message=f"public image target exists but is not a regular file: {image_target}",
        )

    if not source_png.is_file():
        return PublicBlogImageCopyResult(
            status="failed",
            image_relative=image_relative,
            error_message=f"source PNG not found: {source_png}",
        )

    try:
        image_target.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = image_target.with_suffix(image_target.suffix + ".tmp")
        shutil.copy2(source_png, tmp_path)
        try:
            tmp_path.chmod(0o644)
        except OSError:
            pass
        tmp_path.replace(image_target)
        try:
            image_target.chmod(0o644)
        except OSError:
            pass
    except OSError as exc:
        tmp_candidate = image_target.with_suffix(image_target.suffix + ".tmp")
        if tmp_candidate.exists():
            try:
                tmp_candidate.unlink()
            except OSError:
                pass
        return PublicBlogImageCopyResult(
            status="failed",
            image_relative=image_relative,
            error_message=str(exc),
        )

    return PublicBlogImageCopyResult(
        status="copied",
        image_relative=image_relative,
    )


def check_no_overwrite(
    post_target: Path,
    image_target: Path,
    *,
    source_png: Path | None = None,
) -> None:
    conflicts: list[str] = []
    if post_target.exists():
        conflicts.append(str(post_target))
    if image_target.exists():
        if source_png is not None and source_png.is_file():
            try:
                if image_target.read_bytes() == source_png.read_bytes():
                    pass
                else:
                    conflicts.append(str(image_target))
            except OSError:
                conflicts.append(str(image_target))
        else:
            conflicts.append(str(image_target))
    if conflicts:
        joined = "; ".join(conflicts)
        raise PublishError(f"refusing to overwrite existing target(s): {joined}")


def build_plan(
    config: PublishConfig,
    source_slug: str,
    publication_date: date,
    *,
    apply: bool,
    public_slug_override: str | None = None,
) -> PublishPlan:
    public_slug = resolve_public_slug(source_slug, public_slug_override)
    validate_repo_layout(config.repo_path)
    source_md, source_png = resolve_source_paths(config, source_slug)
    post_target, image_target, post_relative, image_relative = target_paths(
        config, public_slug, publication_date
    )
    check_no_overwrite(post_target, image_target, source_png=source_png)

    return PublishPlan(
        source_slug=source_slug,
        public_slug=public_slug,
        publication_date=publication_date,
        mode="apply" if apply else "dry-run",
        source_md=source_md,
        source_png=source_png,
        post_target=post_target,
        image_target=image_target,
        post_relative=post_relative,
        image_relative=image_relative,
        public_url=public_url(config.site_url, publication_date, public_slug),
    )


def apply_plan(plan: PublishPlan) -> None:
    markdown = render_expected_public_post(
        plan.source_md, plan.public_slug, plan.publication_date
    )

    plan.post_target.parent.mkdir(parents=True, exist_ok=True)
    if not plan.image_target.exists():
        plan.image_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plan.source_png, plan.image_target)
    plan.post_target.write_text(markdown, encoding="utf-8")


def plan_to_dict(plan: PublishPlan) -> dict[str, Any]:
    data = asdict(plan)
    data["publication_date"] = plan.publication_date.isoformat()
    data["source_md"] = str(plan.source_md)
    data["source_png"] = str(plan.source_png)
    data["post_target"] = plan.post_relative
    data["image_target"] = plan.image_relative
    return data


def print_summary(plan: PublishPlan) -> None:
    print(f"source_slug: {plan.source_slug}")
    print(f"public_slug: {plan.public_slug}")
    print(f"mode: {plan.mode}")
    print(f"publication_date: {plan.publication_date.isoformat()}")
    print(f"post_target: {plan.post_relative}")
    print(f"image_target: {plan.image_relative}")
    print(f"public_url: {plan.public_url}")
    print(f"status: {plan.status}")


def run_publish(
    source_slug: str,
    *,
    publication_date: date | None = None,
    apply: bool = False,
    json_output: bool = False,
    public_slug_override: str | None = None,
    environ: dict[str, str] | None = None,
) -> PublishPlan:
    import os

    env = os.environ if environ is None else environ
    validate_slug(source_slug, label="source slug")
    if public_slug_override is not None:
        validate_slug(public_slug_override, label="public slug")
    config = load_config(env)
    pub_date = (
        publication_date
        if publication_date is not None
        else parse_publication_date(None)
    )
    plan = build_plan(
        config,
        source_slug,
        pub_date,
        apply=apply,
        public_slug_override=public_slug_override,
    )

    if apply:
        apply_plan(plan)

    if json_output:
        print(json.dumps(plan_to_dict(plan), indent=2))
    else:
        print_summary(plan)

    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare one editorial blog post pair for GitHub Pages "
            "(dry-run by default; use --apply to write files)"
        )
    )
    parser.add_argument(
        "slug",
        help="Source editorial slug shared by .md and .png in blog-posts/ready/",
    )
    parser.add_argument(
        "--public-slug",
        dest="public_slug",
        metavar="SLUG",
        help="Override derived public slug for URLs, filenames, and frontmatter",
    )
    parser.add_argument(
        "--date",
        dest="publication_date",
        metavar="YYYY-MM-DD",
        help="Publication date (default: current UTC date)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write prepared files to the public blog repo checkout",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary",
    )
    args = parser.parse_args(argv)

    try:
        pub_date = (
            parse_publication_date(args.publication_date)
            if args.publication_date is not None
            else None
        )
        run_publish(
            args.slug,
            publication_date=pub_date,
            apply=args.apply,
            json_output=args.json,
            public_slug_override=args.public_slug,
        )
    except PublishError as exc:
        if args.json:
            print(
                json.dumps({"status": "error", "reason": str(exc)}),
                file=sys.stderr,
            )
        else:
            print(f"status: error", file=sys.stderr)
            print(f"reason: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())