// src/lib/subtitles.test.ts
import {toSRT, toVTT} from './subtitles';
import type {TranslatedSegment} from './types';

const makeSegment = (
  original: string,
  translated: string,
  start: number,
  end: number,
): TranslatedSegment => ({original, translated, start, end});

describe('toSRT', () => {
  it('formats a single segment correctly', () => {
    const segments = [makeSegment('Hello', 'Hola', 0, 2.5)];

    expect(toSRT(segments)).toBe(
      '1\n00:00:00,000 --> 00:00:02,500\nHola\n',
    );
  });

  it('formats multiple segments with correct indices', () => {
    const segments = [
      makeSegment('Hello', 'Hola', 0, 2.5),
      makeSegment('World', 'Mundo', 2.5, 5.0),
    ];

    expect(toSRT(segments)).toBe(
      '1\n00:00:00,000 --> 00:00:02,500\nHola\n\n2\n00:00:02,500 --> 00:00:05,000\nMundo\n',
    );
  });

  it('returns empty string for empty segments', () => {
    expect(toSRT([])).toBe('');
  });

  it('formats timestamps exceeding one minute correctly', () => {
    const segments = [makeSegment('Late', 'Tarde', 75.5, 78.123)];

    expect(toSRT(segments)).toBe(
      '1\n00:01:15,500 --> 00:01:18,123\nTarde\n',
    );
  });

  it('formats timestamps exceeding one hour correctly', () => {
    const segments = [makeSegment('Late', 'Tarde', 3661.5, 3663.0)];

    expect(toSRT(segments)).toBe(
      '1\n01:01:01,500 --> 01:01:03,000\nTarde\n',
    );
  });
});

describe('toVTT', () => {
  it('includes WEBVTT header', () => {
    expect(toVTT([])).toBe('WEBVTT\n');
  });

  it('formats a single segment correctly', () => {
    const segments = [makeSegment('Hello', 'Hola', 0, 2.5)];

    expect(toVTT(segments)).toBe(
      'WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nHola\n',
    );
  });

  it('formats multiple segments correctly', () => {
    const segments = [
      makeSegment('Hello', 'Hola', 0, 2.5),
      makeSegment('World', 'Mundo', 2.5, 5.0),
    ];

    expect(toVTT(segments)).toBe(
      'WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nHola\n\n00:00:02.500 --> 00:00:05.000\nMundo\n',
    );
  });

  it('formats timestamps exceeding one minute correctly', () => {
    const segments = [makeSegment('Late', 'Tarde', 75.5, 78.123)];

    expect(toVTT(segments)).toBe(
      'WEBVTT\n\n00:01:15.500 --> 00:01:18.123\nTarde\n',
    );
  });

  it('formats timestamps exceeding one hour correctly', () => {
    const segments = [makeSegment('Late', 'Tarde', 3661.5, 3663.0)];

    expect(toVTT(segments)).toBe(
      'WEBVTT\n\n01:01:01.500 --> 01:01:03.000\nTarde\n',
    );
  });
});