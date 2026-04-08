sudo chmod 666 /run/host-services/ssh-auth.sock

set -euo pipefail

mkdir -p "$HOME/.claude" /tmp/latex-build

# Avoid touching bind-mounted .git metadata that may not allow ownership changes.
sudo find /workspace -mindepth 1 -maxdepth 1 ! -name .git -exec chown -R vscode:vscode {} +
sudo chown -R vscode:vscode "$HOME/.claude" /tmp/latex-build

prek install
