FROM python:3.12-slim

ARG TARGETARCH
RUN ARCH=x86_64; if [ "$TARGETARCH" = "arm64" ]; then ARCH=aarch64; fi; \
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL "https://download.docker.com/linux/static/stable/${ARCH}/docker-27.3.1.tgz" \
       | tar -xz --strip-components=1 -C /usr/local/bin docker/docker \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY patchcourt ./patchcourt

RUN pip install --quiet --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "patchcourt.api.app:app", "--host", "0.0.0.0", "--port", "8000"]