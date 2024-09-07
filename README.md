<h1 align="center">
  <img
    height="150" width="190"
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
