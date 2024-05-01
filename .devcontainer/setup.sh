#!/bin/bash

# Configure baseline git settings
git config --global --add safe.directory ${containerWorkspaceFolder}
git config --global user.email "andrewkimka@gmail.com"
git config --global user.name "Andrew Kim"

# Install font that supports East Asian languages
# Use `fc-list :lang=ko` to verify font is valid
# outside the container.
sudo cp examples/fonts/NotoSerifCJK-Bold.ttc /usr/share/fonts
sudo fc-cache -f -v

# Setup environment
make setup
