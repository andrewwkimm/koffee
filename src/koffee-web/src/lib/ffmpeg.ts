import {FFmpeg} from '@ffmpeg/ffmpeg';
import {fetchFile, toBlobURL} from '@ffmpeg/util';
import type {TranslatedSegment} from './types';
import {toSRT} from './subtitles';

// TODO: support MKV output (requires different subtitle codec e.g. ASS/SSA or SRT in Matroska)
// TODO: expose output filename as a user-configurable option in the UI (Phase 9)

let ffmpeg: FFmpeg | null = null;

const getFFmpeg = (): FFmpeg => {
  if (!ffmpeg) ffmpeg = new FFmpeg();
  return ffmpeg;
};

// --- Helpers ---

export const deriveOutputFilename = (inputName: string): string => {
  const dotIndex = inputName.lastIndexOf('.');
  if (dotIndex === -1) return `${inputName}_subtitled`;
  return `${inputName.slice(0, dotIndex)}_subtitled${inputName.slice(dotIndex)}`;
};

// --- Public API ---

export const initFFmpeg = async (): Promise<void> => {
  const instance = getFFmpeg();
  if (instance.loaded) return;

  const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm';

  await instance.load({
    coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
    wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
  });
};

export const muxSubtitles = async (
  video: File,
  segments: TranslatedSegment[],
): Promise<Blob> => {
  const instance = getFFmpeg();
  const srt = toSRT(segments);
  const outputName = deriveOutputFilename(video.name);

  await instance.writeFile('input.mp4', await fetchFile(video));
  await instance.writeFile('subtitles.srt', srt);

  await instance.exec([
    '-i', 'input.mp4',
    '-i', 'subtitles.srt',
    '-c', 'copy',
    '-c:s', 'mov_text',
    '-metadata:s:s:0', 'language=eng',
    '-y',
    outputName,
  ]);

  const data = await instance.readFile(outputName);

  await instance.deleteFile('input.mp4');
  await instance.deleteFile('subtitles.srt');
  await instance.deleteFile(outputName);

  return new Blob(
    [data instanceof Uint8Array ? data : new TextEncoder().encode(data)],
    {type: 'video/mp4'},
  );
};