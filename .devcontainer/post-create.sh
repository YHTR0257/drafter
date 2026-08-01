set -euo pipefail

curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://claude.ai/install.sh | bash

mkdir -p "$HOME/.claude" /tmp/latex-build

# Avoid touching bind-mounted .git metadata that may not allow ownership changes.
sudo find /workspace -mindepth 1 -maxdepth 1 ! -name .git -exec chown -R vscode:vscode {} +
sudo chown -R vscode:vscode "$HOME/.claude" /tmp/latex-build

prek install
