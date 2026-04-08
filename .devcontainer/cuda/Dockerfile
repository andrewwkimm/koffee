FROM nvidia/cuda:13.0.0-cudnn-devel-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y \
        bash-completion \
        ffmpeg \
    && echo 'source /usr/share/bash-completion/bash_completion' >> /root/.bashrc \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv