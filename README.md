<h1 align="center">
  <img
    src="https://raw.githubusercontent.com/andrewwkimm/koffee/main/assets/koffee.png" alt="koffee logo">
  <br>
</h1>

[![koffee CI](https://github.com/andrewwkimm/koffee/actions/workflows/ci.yaml/badge.svg)](https://github.com/andrewwkimm/koffee/actions)
[![codecov](https://codecov.io/github/andrewwkimm/koffee/graph/badge.svg?token=1AGJM1UMK5)](https://codecov.io/github/andrewwkimm/koffee)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

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


koffee.translate("some_dir/some_video_file.mp4")
```

Here is an example output using a [sample video](examples/videos/sample_korean_video.mp4) from [examples](examples/videos/sample_korean_video.mp4).

https://github.com/user-attachments/assets/3e62d003-5b84-42e4-80b2-13cb89e289e4

## Usage

The koffee CLI has the following structure:

```bash
koffee COMMAND [ARGS] [OPTIONS]
```

Refer below for a list of all arguments, commands, parameters, and options.

### Arguments

    FILE_PATH                   Path to the video, audio, or subtitle file.

### Commands

    info                        Display system information for debugging
    tracks                      List embedded subtitle tracks in a video file.
    transcribe                  Transcribe audio to subtitles without translation.
    convert                     Convert a subtitle file between formats (SRT, VTT, ASS).
    overlay                     Overlay subtitles onto a video without transcription or translation.

### Parameters

    --compute-type, -c          Type to use for computation.
    --device, -d                Device to use for computation.
    --model, -m                 The Whisper model instance to use.
    --output_dir, -o            Directory for the output file.
    --output_name, -n           Name of the output file.
    --source_lang, -sl          Source language (default: auto).
    --target_lang, -t           Language to which the file should be translated.
    --subtitle_format, -sf      Format to use for the subtitles (srt, vtt, ass).
    --translation_backend, -tb  Backend service to use for translation (whisper, gemini).

### Options

    --help, -h                  Display this message and exit.
    --version, -v               Display application version.
    --verbose, -V               Print debug logs.
    --api_key, -ak              API key for LLM based translation.
    --dry-run                   Preview what would be done without processing.
    --overlay                   Subtitle overlay mode: none, soft, or hard.
    --overwrite                 Overwrite existing output files.

## Contributing

The simplest way to start developing is by using either a [DevContainer](https://code.visualstudio.com/docs/devcontainers/containers) or [uv](https://docs.astral.sh/uv/).

If you are planning to develop inside DevContainer, choose the CUDA setup if you have a NVIDIA graphics card and would like to run koffee with CUDA support; otherwise, the default build is much leaner and recommended.

For uv, run the following commands to set up your environment:

```bash
git clone https://github.com/andrewwkimm/koffee.git
cd koffee
pip install pre-commit
make setup
```

## Credits

Special thanks to [Leah Song](https://github.com/leahiscoding) for designing the koffee logo.

Credits to [여배우의 책방](https://www.youtube.com/@onewomansplay2270/featured) for the full version of the sample Korean video.
