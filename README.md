<h1 align="center">
  <img
    src="https://raw.githubusercontent.com/andrewwkimm/koffee/main/assets/koffee.png" alt="koffee logo">
  <br>
</h1>

[![koffee CI](https://github.com/andrewwkimm/koffee/actions/workflows/ci.yaml/badge.svg)](https://github.com/andrewwkimm/koffee/actions)
[![codecov](https://codecov.io/github/andrewwkimm/koffee/graph/badge.svg?token=1AGJM1UMK5)](https://codecov.io/github/andrewwkimm/koffee)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

**koffee** is a tool that automates the translation and subtitling of Korean<>English videos.

## Dependencies

Python versions >=3.10 are supported. Additionally, [ffmpeg](https://www.ffmpeg.org/download.html) is required for koffee to run.

## Installation

koffee can be installed using `pip`.

```console
pip install git+https://github.com/andrewwkimm/koffee
```

## Quick start

All that is needed is a working video file and the translated video will be outputted to the current directory.

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

Refer below for a list of all commands and parameters.

### Parameters

    --file_path                Path to the video file.
    --device, -d               Device used for PyTorch inference.
    --compute_type, -c         Compute type used for the model.
    --model, -m                The Whisper model instance to use.
    --output_dir, -o           Directory for the output file.
    --output_name, -n          Name of the output file.
    --target_language, -t      Language to which the video should be translated.

### Options

    --help, -h                 Display this message and exit.
    --version, -v              Display application version.
    --verbose, -V              Print debug logs.
    --srt, -s                  Write the translated SRT file to disk.

## Contributing

The simplest way to start developing is by using either a [DevContainer](https://code.visualstudio.com/docs/devcontainers/containers) or [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer).

If you are planning to develop inside DevContainer, choose the CUDA setup if you have a NVIDIA graphics card and would like to run koffee with CUDA support; otherwise, the default build is much leaner and recommended.

For Poetry, run the following commands to set up your environment:

```bash
git clone https://github.com/andrewwkimm/koffee.git
cd koffee
pip install pre-commit
make setup
```

## Credits

Special thanks to [Leah Song](https://github.com/leahiscoding) for designing the koffee logo.
