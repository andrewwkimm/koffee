import type {TranslatedSegment} from './types';

const formatTimestamp = (seconds: number, separator: ',' | '.'): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.round((seconds % 1) * 1000);

  const pad2 = (n: number) => String(n).padStart(2, '0');
  const pad3 = (n: number) => String(n).padStart(3, '0');

  return `${pad2(hours)}:${pad2(minutes)}:${pad2(secs)}${separator}${pad3(ms)}`;
};

const formatCue = (segment: TranslatedSegment, separator: ',' | '.', index?: number): string => {
  const start = formatTimestamp(segment.start, separator);
  const end = formatTimestamp(segment.end, separator);
  const indexLine = index !== undefined ? `${index}\n` : '';

  return `${indexLine}${start} --> ${end}\n${segment.translated}\n`;
};

export const toSRT = (segments: TranslatedSegment[]): string => {
  if (segments.length === 0) return '';

  return segments
    .map((seg, i) => formatCue(seg, ',', i + 1))
    .join('\n');
};

export const toVTT = (segments: TranslatedSegment[]): string => {
  const header = 'WEBVTT\n';

  if (segments.length === 0) return header;

  const cues = segments.map((seg) => formatCue(seg, '.')).join('\n');

  return `${header}\n${cues}`;
};