FROM texlive/texlive:latest

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc fontconfig \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PROJECT_ENVIRONMENT=/opt/drafter-venv
WORKDIR /opt/drafter
COPY pyproject.toml uv.lock ./
RUN uv python install 3.12 \
    && uv sync --locked --no-dev --no-install-project --python 3.12

# Dependencies live in the image; project sources are read from the bind mount.
# Arbitrary host UID/GID must be able to write TeX caches without a passwd entry.
ENV UV_NO_SYNC=1 \
    PYTHONPATH=/workspace/src \
    HOME=/tmp \
    TEXMFVAR=/tmp/texmf-var \
    TEXMFCONFIG=/tmp/texmf-config \
    TEXMFCACHE=/tmp/texmf-var
WORKDIR /workspace
CMD ["sleep", "infinity"]
