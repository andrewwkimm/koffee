import {FFmpeg} from '@ffmpeg/ffmpeg';
import {fetchFile, toBlobURL} from '@ffmpeg/util';
import type {TranslatedSegment} from './types';
import {toSRT} from './subtitles';

let ffmpeg: FFmpeg | null = null;
let loadPromise: Promise<void> | null = null;

export const deriveOutputFilename = (inputName: string): string => {
  const dotIndex = inputName.lastIndexOf('.');
  if (dotIndex === -1) return `${inputName}_subtitled`;
  return `${inputName.slice(0, dotIndex)}_subtitled${inputName.slice(dotIndex)}`;
};

export const initFFmpeg = async (): Promise<void> => {
  if (loadPromise) return loadPromise;

  loadPromise = (async () => {
    ffmpeg = new FFmpeg();

    ffmpeg.on('log', ({message}) => {
      console.log('[ffmpeg log]', message);
    });

    const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm';

    await ffmpeg.load({
      coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
      wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
    });

    console.log('[ffmpeg] loaded');
  })();

  return loadPromise;
};

export const muxSubtitles = async (
  video: File,
  segments: TranslatedSegment[],
): Promise<Blob> => {
  // Always ensure ffmpeg is loaded before muxing
  await initFFmpeg();

  const instance = ffmpeg!;
  const srt = toSRT(segments);

  const INPUT = 'input.mp4';
  const SUBS = 'subs.srt';
  const OUTPUT = 'output.mp4';

  console.log('[ffmpeg] srt content:', srt);
  console.log('[ffmpeg] writing files...');

  await instance.writeFile(INPUT, await fetchFile(video));
  await instance.writeFile(SUBS, srt);

  console.log('[ffmpeg] running exec...');

  const exitCode = await instance.exec([
    '-i', INPUT,
    '-i', SUBS,
    '-c', 'copy',
    '-c:s', 'mov_text',
    '-metadata:s:s:0', 'language=eng',
    '-y',
    OUTPUT,
  ]);

  console.log('[ffmpeg] exec exit code:', exitCode);

  if (exitCode !== 0) {
    throw new Error(`FFmpeg exited with code ${exitCode}`);
  }

  console.log('[ffmpeg] reading output...');

  const data = await instance.readFile(OUTPUT);

  await instance.deleteFile(INPUT);
  await instance.deleteFile(SUBS);
  await instance.deleteFile(OUTPUT);

  const outputName = deriveOutputFilename(video.name);

  return new Blob(
    [data instanceof Uint8Array ? data : new TextEncoder().encode(data)],
    {type: 'video/mp4'},
  );
};