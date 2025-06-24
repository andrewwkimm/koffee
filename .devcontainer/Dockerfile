# See here for image contents: https://github.com/devcontainers/templates/tree/main/src/ubuntu

FROM mcr.microsoft.com/devcontainers/base:jammy

RUN \
    apt update \
    && apt upgrade -y \
    && apt install -y bash-completion curl ffmpeg

# Coding only for vscode user and not root
USER vscode

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && bash -c "echo 'source <(poetry completions bash)' >> ~/.bashrc"
