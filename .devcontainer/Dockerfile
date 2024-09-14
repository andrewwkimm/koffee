FROM nvcr.io/nvidia/cuda:12.5.1-cudnn-devel-ubuntu22.04

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN \
  apt-get upgrade \
  && apt-get update \
  && apt-get -y install bash-completion curl ffmpeg git libcudnn8 libcudnn8-dev python3 python3-pip \
  && pip install nox pre-commit

# Create a symlink from python3 to python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Install Nvidia Container Toolkit to run container on GPU
RUN \
	curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
	gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list \
    && apt-get update \
    && apt-get install -y nvidia-container-toolkit

# Coding only for vscode user and not root
RUN \
    groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME

USER $USERNAME

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
  && bash -c "echo 'source <(poetry completions bash)' >> ~/.bashrc"

ENV PATH="/home/vscode/.local/bin:$PATH"
