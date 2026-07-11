FROM python:3.11-slim

ARG BUILD_REVISION=unknown
ENV BUILD_REVISION=${BUILD_REVISION}

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY prompts ./prompts

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git --version

RUN pip install --no-cache-dir .

ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn silverman_blog_linkedin.main:create_app --host 0.0.0.0 --port ${PORT} --factory"]
