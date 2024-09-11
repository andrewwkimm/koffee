#!/bin/bash

# Add current workspace as a safe directory
git config --global --add safe.directory $(pwd)

# Prompt user for Git username and email
read -p "Enter your Git username: " git_username
read -p "Enter your Git email: " git_email

# Configure baseline git settings
git config --global user.email "$git_email"
git config --global user.name "$git_username"

# Install font that supports East Asian languages
# Use `fc-list :lang=ko` to verify font is valid outside the container.
sudo cp examples/fonts/NotoSerifCJK-Bold.ttc /usr/share/fonts
sudo fc-cache -f -v

# Setup environment and activate poetry's virtual environment
make setup && poetry shell
