FROM python:3.11-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /install

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m venv /opt/lcc \
    && /opt/lcc/bin/pip install --upgrade pip \
    && /opt/lcc/bin/pip install .

FROM python:3.11-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LCC_CACHE_DIR=/var/cache/lcc \
    PASSLIB_MAX_PASSWORD_SIZE=4096
RUN apk add --no-cache git \
    && addgroup -S lcc && adduser -S lcc -G lcc \
    && mkdir -p ${LCC_CACHE_DIR} /workspace /var/lib/lcc \
    && chown -R lcc:lcc ${LCC_CACHE_DIR} /workspace /var/lib/lcc

COPY --from=builder /opt/lcc /opt/lcc

USER lcc
WORKDIR /workspace

ENV PATH="/opt/lcc/bin:$PATH"

VOLUME ["/workspace", "/var/lib/lcc"]

ENTRYPOINT ["lcc"]
CMD ["--help"]

HEALTHCHECK --interval=1m --timeout=10s --start-period=30s --retries=3 \
    CMD lcc --version || exit 1
