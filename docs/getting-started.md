# Getting started

## Installation

**Prerequisites**
* Python 3.11 – 3.13
* [ffmpeg](https://www.ffmpeg.org/download.html) (must be in system PATH)

**Install via pip**
```console
pip install git+https://github.com/andrewwkimm/koffee
```

## Usage

Video, audio, and subtitle files are all supported for translation and the translated subtitle file will be outputted to the current directory.

```console
koffee some_dir/some_video_file.mp4
```

The translation method defaults to Whisper; for more accurate translations, koffee supports LLM (currently ChatGPT, Claude, Gemini, and Ollama) based translations as well.

Set your API key as an environment variable to use but it also passable as an argument.

```console
export GEMINI_API_KEY=<your-api-key>
koffee audio_file.mp3 --translator=gemini
```

or

```
koffee audio_file.mp3 --translator=gemini --api-key=<your-api-key>
```

There is full feature parity between the CLI and the Python library. See the example below for basic usage:

```python
import koffee


koffee.translate("some_dir/some_video_file.mp4")
```