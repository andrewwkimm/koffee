#!/bin/bash

# Change ownership to non-root user
chown -R vscode:vscode "$(pwd)"

# Load .env file if it exists
if [[ -f .env ]]; then
    source .env
fi

# Prompt for missing values
if [[ -z "$GIT_USERNAME" ]]; then
    read -p "Enter your Git username: " GIT_USERNAME
fi

if [[ -z "$GIT_EMAIL" ]]; then
    read -p "Enter your Git email: " GIT_EMAIL
fi

# Ask to save to .env if values were entered manually
if [[ ! -f .env ]] || ! grep -q "GIT_USERNAME\|GIT_EMAIL" .env 2>/dev/null; then
    read -p "Save Git credentials to .env? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        {
            echo "GIT_USERNAME=$GIT_USERNAME"
            echo "GIT_EMAIL=$GIT_EMAIL"
        } >> .env
        echo "Saved to .env file."
    fi
fi

# Configure git
git config --global user.name "$GIT_USERNAME"
git config --global user.email "$GIT_EMAIL"
git config --global core.editor "code --wait"
git config --global --add safe.directory "$(pwd)"

# Setup environment
pip install pre-commit nox
make setup
