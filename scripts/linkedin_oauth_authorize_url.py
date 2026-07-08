#!/usr/bin/env python3
"""Print LinkedIn OAuth authorization URL for local operator use."""

from __future__ import annotations

import argparse
import os
import sys

from silverman_blog_linkedin.linkedin_oauth_flow import build_authorize_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print LinkedIn OAuth authorization URL (no secrets)."
    )
    parser.parse_args(argv)

    result = build_authorize_result(os.environ)
    if result.status != "completed" or not result.authorization_url:
        errors = ", ".join(result.errors) if result.errors else "unknown error"
        print(f"Failed to build authorization URL: {errors}", file=sys.stderr)
        return 1

    print(result.authorization_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
