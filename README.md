<h1 align="center">
  <img
    height="250" width="390"
    src="https://raw.githubusercontent.com/andrewwkimm/koffee/main/assets/koffee.png" alt="koffee logo">
  <br>
</h1>

[![koffee CI](https://github.com/andrewwkimm/koffee/actions/workflows/ci.yaml/badge.svg)](https://github.com/andrewwkimm/koffee/actions)

**koffee** is a tool that automates the translation and subtitling of Korean<>English videos.

## Dependencies

Python versions >=3.10 are supported. Additionally, [ffmpeg](https://www.ffmpeg.org/download.html) is required for koffee to run.

## Installation

koffee can be installed using `pip`.

```console
pip install koffee
```

## Quick start

All that is needed is a working video file and the translated video will be outputted to the current directory.

```console
koffee some_dir/some_video_file.mp4
```

Alternatively, usage through Python is also available.

```python
from koffee import translate


translate("some_dir/some_video_file.mp4")
```

Here is an example output using a [sample video](examples/videos/sample_korean_video.mp4) from [examples](examples/videos/sample_korean_video.mp4).

https://github.com/user-attachments/assets/8b899ac0-fd8d-420f-87d9-505347a149fd

## Usage

The koffee CLI has the following structure:

```bash
koffee COMMAND [ARGS] [OPTIONS]
```

Refer below for a list of all commands and parameters.

### Commands

    --help, -h                 Display this message and exit.
    --version, -v              Display application version.

### Parameters

    --file_path               Path to the video file.
    --batch_size              Batch size used when transcribing the audio.
    --device                  Device used for PyTorch inference.
    --compute_type            Compute type used for the model.
    --model                   The Whisper model instance to use.
    --output_dir              Directory for the output file.
    --output_name             Name of the output file.
