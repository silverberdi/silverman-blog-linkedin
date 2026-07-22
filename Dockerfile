FROM python:3.11-slim

# Worker API image is API-only (US-096 / BL-034). Do not embed the operator
# console SPA (no frontend production embed step; do not copy Vite assets into
# src/.../static/). Supported production console: separated UI image
# (frontend/linkedin-variant-supervision-console/Dockerfile, compose
# silverman-operator-ui on LAN :8011).

ARG BUILD_REVISION=unknown
ENV BUILD_REVISION=${BUILD_REVISION}

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY prompts ./prompts
COPY content-strategy ./content-strategy

RUN apt-get update \
    && apt-get install -y --no-install-recommends git openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && git --version \
    && git config --system safe.directory '*' \
    && git config --system user.email 'silverman-blog-linkedin-worker@users.noreply.local' \
    && git config --system user.name 'silverman-blog-linkedin-worker'

RUN pip install --no-cache-dir .

ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn silverman_blog_linkedin.main:create_app --host 0.0.0.0 --port ${PORT} --factory"]
