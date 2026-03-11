// src/lib/ffmpeg.test.ts
import {initFFmpeg, muxSubtitles, deriveOutputFilename} from './ffmpeg';
import type {TranslatedSegment} from './types';

let mockFFmpegInstance: {
  loaded: boolean;
  load: ReturnType<typeof vi.fn>;
  writeFile: ReturnType<typeof vi.fn>;
  exec: ReturnType<typeof vi.fn>;
  readFile: ReturnType<typeof vi.fn>;
  deleteFile: ReturnType<typeof vi.fn>;
};

vi.mock('@ffmpeg/ffmpeg', () => ({
  FFmpeg: vi.fn().mockImplementation(function (this: typeof mockFFmpegInstance) {
    this.loaded = false;
    this.load = vi.fn().mockResolvedValue(undefined);
    this.writeFile = vi.fn().mockResolvedValue(undefined);
    this.exec = vi.fn().mockResolvedValue(undefined);
    this.readFile = vi.fn().mockResolvedValue(new Uint8Array());
    this.deleteFile = vi.fn().mockResolvedValue(undefined);
    mockFFmpegInstance = this;
  }),
}));

vi.mock('@ffmpeg/util', () => ({
  fetchFile: vi.fn().mockResolvedValue(new Uint8Array()),
  toBlobURL: vi.fn().mockResolvedValue('blob:mock'),
}));

const makeSegment = (
  original: string,
  translated: string,
  start: number,
  end: number,
): TranslatedSegment => ({original, translated, start, end});

describe('deriveOutputFilename', () => {
  it('appends _translated before the extension', () => {
    expect(deriveOutputFilename('video.mp4')).toBe('video_translated.mp4');
  });

  it('handles filenames with multiple dots', () => {
    expect(deriveOutputFilename('my.video.mp4')).toBe('my.video_translated.mp4');
  });

  it('handles filenames with no extension', () => {
    expect(deriveOutputFilename('video')).toBe('video_translated');
  });
});

describe('initFFmpeg', () => {
  it('calls load with core and wasm URLs', async () => {
    await initFFmpeg();

    expect(mockFFmpegInstance.load).toHaveBeenCalledWith({
      coreURL: 'blob:mock',
      wasmURL: 'blob:mock',
    });
  });

  it('does not call load if already loaded', async () => {
    mockFFmpegInstance.loaded = true;

    await initFFmpeg();

    expect(mockFFmpegInstance.load).not.toHaveBeenCalled();
  });
});

describe('muxSubtitles', () => {
  it('writes input video and srt to ffmpeg filesystem', async () => {
    const file = new File(['content'], 'video.mp4', {type: 'video/mp4'});
    const segments = [makeSegment('Hello', 'Hola', 0, 2.5)];

    await muxSubtitles(file, segments);

    expect(mockFFmpegInstance.writeFile).toHaveBeenCalledWith('input.mp4', expect.any(Uint8Array));
    expect(mockFFmpegInstance.writeFile).toHaveBeenCalledWith('subtitles.srt', expect.any(String));
  });

  it('executes ffmpeg with correct soft subtitle arguments', async () => {
    const file = new File(['content'], 'video.mp4', {type: 'video/mp4'});
    const segments = [makeSegment('Hello', 'Hola', 0, 2.5)];

    await muxSubtitles(file, segments);

    expect(mockFFmpegInstance.exec).toHaveBeenCalledWith([
      '-i', 'input.mp4',
      '-i', 'subtitles.srt',
      '-c', 'copy',
      '-c:s', 'mov_text',
      '-metadata:s:s:0', 'language=eng',
      '-y',
      'video_translated.mp4',
    ]);
  });

  it('cleans up ffmpeg filesystem after muxing', async () => {
    const file = new File(['content'], 'video.mp4', {type: 'video/mp4'});
    const segments = [makeSegment('Hello', 'Hola', 0, 2.5)];

    await muxSubtitles(file, segments);

    expect(mockFFmpegInstance.deleteFile).toHaveBeenCalledWith('input.mp4');
    expect(mockFFmpegInstance.deleteFile).toHaveBeenCalledWith('subtitles.srt');
    expect(mockFFmpegInstance.deleteFile).toHaveBeenCalledWith('video_translated.mp4');
  });

  it('returns a video/mp4 blob', async () => {
    const file = new File(['content'], 'video.mp4', {type: 'video/mp4'});
    const segments = [makeSegment('Hello', 'Hola', 0, 2.5)];

    const result = await muxSubtitles(file, segments);

    expect(result).toBeInstanceOf(Blob);
    expect(result.type).toBe('video/mp4');
  });
});