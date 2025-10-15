# See here for image contents: https://github.com/devcontainers/templates/tree/main/src/ubuntu

FROM mcr.microsoft.com/devcontainers/base:jammy

RUN \
    apt update \
    && apt upgrade -y \
    && apt install -y bash-completion curl \
    # Install FFmpeg 7.x static build
    && cd /tmp \
    && wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar xvf ffmpeg-release-amd64-static.tar.xz \
    && cd ffmpeg-*-amd64-static \
    && cp ffmpeg ffprobe /usr/local/bin/ \
    && chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe \
    # Clean up
    && cd / \
    && rm -rf /tmp/ffmpeg-* \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# Coding only for vscode user and not root
USER vscode

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
