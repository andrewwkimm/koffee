# Getting started

## **Installation**

**Prerequisites**
* Python 3.11 – 3.13
* [ffmpeg](https://www.ffmpeg.org/download.html) (Must be in system PATH. Hard burn-in (`--embed=hard`) needs a build with libass; macOS users installing from Homebrew need to use `brew install ffmpeg-full`)

**Install via pip**
```console
pip install git+https://github.com/andrewwkimm/koffee
```

## **Usage**

Video, audio, and subtitle files are all supported for translation and the translated subtitle file will be outputted to the current directory.

```console
koffee some_dir/some_video_file.mp4
```

The translation method defaults to Whisper; for more accurate translations, koffee supports LLM (currently ChatGPT, Claude, Gemini, and Ollama) based translations as well.

Set your API key as an environment variable to use but it also passable as an argument.

```console
export GOOGLE_API_KEY=<your-api-key>
koffee audio_file.mp3 --translator=google
```

or

```
koffee audio_file.mp3 --translator=google --api-key=<your-api-key>
```

There is full feature parity between the CLI and the Python library. See the example below for basic usage:

```python
import koffee


koffee.run("some_dir/some_video_file.mp4")
```

## Output naming and embedded subtitles

Default output names are deterministic. Translated subtitles use
`<input>.<target-language>.<format>`, while embedded videos use
`<input>.<target-language>.<soft|hard>.<container>`. An explicit
`--output-name` is exact: koffee does not append or replace a suffix, so include the
extension yourself when one is wanted.

Soft subtitle embedding is supported for MP4, M4V, MOV, MKV, and WebM outputs.
Other supported video containers can still be translated and can use hard burn-in,
but cannot receive a soft subtitle stream.

Embedded subtitle selection uses the subtitle ordinal reported by FFmpeg (the value
used by `0:s:<ordinal>`), not the absolute stream index and not the position in a
filtered list. Bitmap subtitle streams still count toward this ordinal even though
koffee lists and translates only text subtitle streams. Interactive menus show a
menu position and also show the actual subtitle ordinal whenever those values differ.
