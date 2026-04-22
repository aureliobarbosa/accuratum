#!/bin/bash
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
