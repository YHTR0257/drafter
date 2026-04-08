FROM texlive/texlive:latest

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    sudo \
    curl \
    wget \
    unzip \
    nodejs \
    npm \
    pandoc \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Install Gemini CLI
RUN npm install -g @google/gemini-cli

ENV DEVCONTAINER=true

# 必要なディレクトリを作成（common-utils featureがvscodeユーザーを作成する）
RUN mkdir -p /workspace

# フォントのコピーとインストール（.devcontainer/fontsディレクトリから）
COPY .devcontainer/fonts /usr/share/fonts/ms-fonts/
RUN fc-cache -fv
