#!/bin/bash

# Add current workspace as a safe directory
git config --global --add safe.directory $(pwd)

# Prompt user for Git username and email
read -p "Enter your Git username: " git_username
read -p "Enter your Git email: " git_email

# Configure baseline git settings
git config --global user.email "$git_email"
git config --global user.name "$git_username"

# Set VS Code as the default text editor
git config --global core.editor "code --wait"

# Setup environment and activate poetry's virtual environment
make setup
