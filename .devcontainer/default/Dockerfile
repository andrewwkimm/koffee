# See here for image contents: https://github.com/devcontainers/templates/tree/main/src/ubuntu

FROM mcr.microsoft.com/devcontainers/base:jammy

RUN \
    apt update \
    && apt upgrade -y \
    && apt install -y bash-completion curl ffmpeg

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
