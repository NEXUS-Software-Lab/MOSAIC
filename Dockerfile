# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS builder

# Some Androguard dependencies contain native extensions.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLCONFIGDIR=/tmp/matplotlib

COPY --from=builder /opt/venv /opt/venv
RUN groupadd --gid 10001 mosaic \
    && useradd --uid 10001 --gid mosaic --create-home mosaic \
    && mkdir /data \
    && chown mosaic:mosaic /data

WORKDIR /data
USER mosaic
ENTRYPOINT ["mosaic"]
CMD ["--help"]
