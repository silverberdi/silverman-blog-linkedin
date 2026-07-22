FROM python:3.11-slim

# Before building this image, rebuild embedded console static assets so COPY src includes them:
#   cd frontend/linkedin-variant-supervision-console && npm ci && npm run build:embedded
# The runtime image has no Node — worker may serve prebuilt Vite artifacts as a
# compatibility path only. Supported production console path is the separated
# operator UI image (see frontend/.../Dockerfile, compose silverman-operator-ui).

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
