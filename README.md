<h1 align="center">
  <img
    src="https://raw.githubusercontent.com/andrewwkimm/koffee/main/docs/assets/logo.png" alt="koffee logo">
  <br>
</h1>

[![koffee CI](https://github.com/andrewwkimm/koffee/actions/workflows/ci.yaml/badge.svg)](https://github.com/andrewwkimm/koffee/actions)
![Docs](https://github.com/andrewwkimm/koffee/actions/workflows/docs.yaml/badge.svg)
[![codecov](https://codecov.io/github/andrewwkimm/koffee/graph/badge.svg?token=1AGJM1UMK5)](https://codecov.io/github/andrewwkimm/koffee)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

---

**Source Code**: https://github.com/andrewwkimm/koffee

**Documentation**: https://andrewwkimm.github.io/koffee

---

**koffee** is a tool that automates the translation and subtitling of video and audio files.

## Dependencies

Python versions 3.11 to 3.13 are supported. Additionally, [ffmpeg](https://www.ffmpeg.org/download.html) is required for koffee to run.

## Installation

koffee can be installed using `pip`.

```console
pip install git+https://github.com/andrewwkimm/koffee
```

## Quick start

All that is needed is a working video, audio, or subtitle file and the translated subtitle file will be outputted to the current directory.

```console
koffee some_dir/some_video_file.mp4
```

Alternatively, usage through Python is also available.

```python
import koffee


koffee.run("some_dir/some_video_file.mp4")
```

Here is an example output using a [sample video](examples/videos/sample_korean_video.mp4) from [examples](examples/).

https://github.com/user-attachments/assets/481f38cb-ac62-422f-9334-69fab669424e

## Usage

The koffee CLI has the following structure:

```bash
koffee COMMAND [ARGS] [OPTIONS]
```

Refer below for a list of all arguments, commands, parameters, and options.

### Arguments

    FILE_PATH  Path to the video, audio, or subtitle file

### Commands

    info        Display system information for debugging
    languages   Display all supported languages
    tracks      List embedded subtitle tracks in a video file
    transcribe  Transcribe audio to subtitles without translation
    convert     Convert a subtitle file between formats (SRT, VTT, ASS)
    overlay     Overlay subtitles onto a video without transcr     translation

### Parameters

    --compute-type          -c  Type to use for computation
    --device                -d  Device to use for computation
    --whisper-model         -m  The Whisper model instance to use
    --output-dir            -o  Directory for the output file
    --output-name           -n  Name of the output file
    --source-language       -s  Source language of the subtitle file (default: auto)
    --target-language       -t  Language to which the file should be translated
    --subtitle-format       -f  Format to use for the subtitles
    --embed                     Subtitle embed mode: none, soft, or hard
    --translator                The backend service to use for the translation (whisper, gemini, chatgpt, claude, ollama)
    --llm-model                 The LLM model to use for translation
    --chunk-size                Number of subtitle entries per LLM request (auto-selected per model if unset)
    --context-size              Number of preceding entries passed as context per request (auto-selected per model if unset)
    --prompt                    Custom system prompt for the LLM translation model
    --api-key                   API key for an LLM service

### Options

    --config                    Path to a koffee.toml configuration file
    --dry-run                   Preview what files would be processed
    --overwrite                 Overwrite existing output files instead of raising an error
    --verbose               -v  Print debug log messages
    --help                  -h  Display this message and exit
    --version               -V  Display application version

## Configuration

koffee can be configured with a `koffee.toml` file. It searches for the file in the following locations (in order):

1. Current working directory: `./koffee.toml`
2. User config directory: `~/.config/koffee/koffee.toml`

Settings follow this precedence: **defaults < config file < CLI arguments**.

Example `koffee.toml`:

```toml
compute-type = "float16"
device = "cuda"
whisper-model = "large-v3"
source-language = "ko"
target-language = "en"
subtitle-format = "srt"
translator = "gemini"
llm-model = "gemini-2.5-flash"
chunk-size = 400
context-size = 20
```

## Contributing

The simplest way to start developing is by using either a [DevContainer](https://code.visualstudio.com/docs/devcontainers/containers) or directly only use [uv](https://docs.astral.sh/uv/) in your local machine.

If you are planning to develop inside DevContainer, choose the CUDA setup if you have a NVIDIA graphics card and would like to run koffee with CUDA support; otherwise, the default build is much leaner and recommended.

For uv, run the following commands to set up your environment:

```bash
git clone https://github.com/andrewwkimm/koffee.git
cd koffee
make setup
```

## Credits

Special thanks to [Leah Song](https://github.com/leahiscoding) for designing the koffee logo.

Credits to [여배우의 책방](https://www.youtube.com/@onewomansplay2270/featured) for the full version of the sample Korean video.
