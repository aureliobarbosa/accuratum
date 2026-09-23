#!/bin/bash
# Claude Code config: the named volume is created root-owned
CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-/home/vscode/.claude-code}"
sudo chown vscode:vscode "$CLAUDE_CONFIG_DIR"

# Seed per-machine Claude settings (settings.json is not synced)
if [ ! -f "$CLAUDE_CONFIG_DIR/settings.json" ]; then
  cat > "$CLAUDE_CONFIG_DIR/settings.json" << 'EOF'
{
  "model": "opus",
  "effortLevel": "medium",
  "agentPushNotifEnabled": true,
  "cleanupPeriodDays": 100000
}
EOF
fi

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
$HOME/.local/bin/uv sync --extra dev

# Register Jupyter kernel
python -m ipykernel install --user --name=accuratum --display-name='Python (accuratum)'

# Prompt for git user config on first terminal open
cat >> ~/.bashrc << 'EOF'
if [ -z "$(git config --global user.email)" ]; then
  echo "Git user not configured."
  read -p "Enter your name: " git_name
  read -p "Enter your email: " git_email
  git config --global user.name "$git_name"
  git config --global user.email "$git_email"
fi
EOF
