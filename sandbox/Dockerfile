FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir semgrep bandit radon

RUN curl -fsSL https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz \
    | tar -xz -C /usr/local/bin gitleaks

WORKDIR /workspace
COPY run_tools.py /usr/local/bin/run-tools.py

ENTRYPOINT ["python", "/usr/local/bin/run-tools.py"]