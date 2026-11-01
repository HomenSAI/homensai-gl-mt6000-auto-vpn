# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
# External QA toolbox (2026-11-01): static analysers, fuzzing toolchain, secret scanner. Offline-safe: no router access.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git make gcc libc6-dev clang llvm lld cppcheck shellcheck lua5.1 liblua5.1-0-dev luarocks \
      python3 python3-venv python3-pip nodejs npm xz-utils \
 && rm -rf /var/lib/apt/lists/*
RUN luarocks install luacheck 1.2.0-1
RUN python3 -m venv /opt/py && /opt/py/bin/pip install --no-cache-dir \
      bandit==1.8.6 ruff==0.14.3 pyflakes==3.4.0 hypothesis==6.142.4 mutmut==3.3.1
RUN mkdir /opt/eslint && cd /opt/eslint && npm init -y >/dev/null && npm install --no-audit --no-fund eslint@9.39.0 globals@16.5.0 @eslint/js@9.39.0
RUN curl -fsSL https://github.com/gitleaks/gitleaks/releases/download/v8.28.0/gitleaks_8.28.0_linux_x64.tar.gz | tar -xz -C /usr/local/bin gitleaks
RUN curl -fsSL https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz | tar -xJ -C /tmp && mv /tmp/shellcheck-v0.11.0/shellcheck /usr/local/bin/shellcheck
RUN curl -fsSL https://www.lua.org/ftp/lua-5.1.5.tar.gz | tar -xz -C /opt
# libFuzzer/ASan runtimes for clang 18 (qa/external/fuzz/run.sh)
RUN apt-get update && apt-get install -y --no-install-recommends libclang-rt-18-dev && rm -rf /var/lib/apt/lists/*
# semgrep: the official image semgrep/semgrep:1.142.0 is used instead (the PyPI wheel's mcp/pydantic pins clash here)
ENV PATH=/opt/py/bin:/opt/eslint/node_modules/.bin:$PATH
WORKDIR /src
