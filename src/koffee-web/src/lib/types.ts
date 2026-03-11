interface Segment {
  text: string;
  start: number;
  end: number;
}

interface TranslatedSegment {
  original: string;
  translated: string;
  start: number;
  end: number;
}

// Message types
type WorkerMessage =
  | {type: 'segment'; payload: Segment}
  | {type: 'done'}
  | {type: 'error'; payload: {code: string; message: string; fatal: boolean}};