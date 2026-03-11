import {useState, useRef, useCallback, useEffect} from 'react';
import type React from 'react';
import {DropZone} from './components/DropZone';
import {initFFmpeg, muxSubtitles, deriveOutputFilename} from './lib/ffmpeg';
import {decodeAudio} from './lib/audio';
import {SUPPORTED_LANGUAGES} from './lib/languages';
import type {
  Segment,
  TranslatedSegment,
  WhisperMessage,
  TranslateMessage,
  TranslateWorkerInbound,
} from './lib/types';
import {createWhisperWorker, createTranslateWorker} from './lib/workerFactory';

// --- Types ---

type PipelineStatus = 'idle' | 'transcribing' | 'translating' | 'muxing' | 'done' | 'error';

interface AppState {
  file: File | null;
  segments: TranslatedSegment[];
  status: PipelineStatus;
  error: string | null;
}

const INITIAL_STATE: AppState = {
  file: null,
  segments: [],
  status: 'idle',
  error: null,
};

// --- Component ---

export default function App() {
  const [state, setState] = useState<AppState>(INITIAL_STATE);

  // Language state in refs to avoid stale closures in worker callbacks
  const sourceLanguageRef = useRef<string>('auto');
  const targetLanguageRef = useRef<string>('en');

  // Segments and file in refs to avoid stale closures in async callbacks
  const segmentsRef = useRef<TranslatedSegment[]>([]);
  const fileRef = useRef<File | null>(null);

  // Translate worker readiness and segment buffer
  const translateReadyRef = useRef(false);
  const segmentBufferRef = useRef<Segment[]>([]);

  const whisperWorkerRef = useRef<Worker | null>(null);
  const translateWorkerRef = useRef<Worker | null>(null);

  useEffect(() => {
    initFFmpeg().catch((err: unknown) => {
      console.error('ffmpeg failed to load:', err);
    });
  }, []);

  const terminateWorkers = useCallback(() => {
    whisperWorkerRef.current?.terminate();
    translateWorkerRef.current?.terminate();
    whisperWorkerRef.current = null;
    translateWorkerRef.current = null;
  }, []);

  const initTranslateWorker = useCallback(
    (sourceLanguage: string, targetLanguage: string) => {
      const payload: TranslateWorkerInbound = {
        type: 'init',
        payload: {sourceLanguage, targetLanguage},
      };
      translateWorkerRef.current?.postMessage(payload);
    },
    [],
  );

  const flushSegmentBuffer = useCallback(() => {
    for (const segment of segmentBufferRef.current) {
      translateWorkerRef.current?.postMessage({
        type: 'segment',
        payload: segment,
      });
    }
    segmentBufferRef.current = [];
  }, []);

  const handleTranslateMessage = useCallback(
    (e: MessageEvent<TranslateMessage>) => {
      const msg = e.data;

      if (msg.type === 'ready') {
        translateReadyRef.current = true;
        flushSegmentBuffer();
        return;
      }

      if (msg.type === 'segment') {
        segmentsRef.current = [...segmentsRef.current, msg.payload];
        setState((prev) => ({
          ...prev,
          segments: segmentsRef.current,
        }));
        return;
      }

      if (msg.type === 'done') {
        setState((prev) => ({...prev, status: 'muxing'}));

        // fileRef is guaranteed non-null here — pipeline only starts on file drop
        muxSubtitles(fileRef.current!, segmentsRef.current)
          .then((blob) => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = deriveOutputFilename(fileRef.current!.name);
            a.click();
            URL.revokeObjectURL(url);
            setState((prev) => ({...prev, status: 'done'}));
          })
          .catch((err: unknown) => {
            setState((prev) => ({
              ...prev,
              status: 'error',
              error: err instanceof Error ? err.message : 'Muxing failed',
            }));
          })
          .finally(() => {
            terminateWorkers();
          });

        return;
      }

      if (msg.type === 'error' && msg.payload.fatal) {
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: msg.payload.message,
        }));
        terminateWorkers();
        return;
      }

      // non-fatal translate error — pipeline continues, segment is silently skipped
      // original text substitution is handled inside the translate worker
    },
    [terminateWorkers, flushSegmentBuffer],
  );

  const handleWhisperMessage = useCallback(
    (e: MessageEvent<WhisperMessage>) => {
      const msg = e.data;

      if (msg.type === 'segment') {
        const segment = msg.payload as Segment;

        if (translateReadyRef.current) {
          translateWorkerRef.current?.postMessage({
            type: 'segment',
            payload: segment,
          });
        } else {
          segmentBufferRef.current = [...segmentBufferRef.current, segment];
        }
        return;
      }

      if (msg.type === 'done') {
        const sourceLanguage =
          sourceLanguageRef.current === 'auto'
            ? msg.payload.language
            : sourceLanguageRef.current;

        sourceLanguageRef.current = sourceLanguage;

        setState((prev) => ({...prev, status: 'translating'}));
        initTranslateWorker(sourceLanguage, targetLanguageRef.current);
        return;
      }

      if (msg.type === 'error' && msg.payload.fatal) {
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: msg.payload.message,
        }));
        terminateWorkers();
      }
    },
    [initTranslateWorker, terminateWorkers],
  );

  const handleFileDrop = useCallback(
    (file: File) => {
      terminateWorkers();

      // Reset all refs for fresh run
      segmentsRef.current = [];
      fileRef.current = file;
      translateReadyRef.current = false;
      segmentBufferRef.current = [];

      setState({...INITIAL_STATE, file, status: 'transcribing'});

      const whisperWorker = createWhisperWorker();
      const translateWorker = createTranslateWorker();

      whisperWorker.onmessage = handleWhisperMessage;
      translateWorker.onmessage = handleTranslateMessage;

      whisperWorkerRef.current = whisperWorker;
      translateWorkerRef.current = translateWorker;

      // If source language is pre-selected, init translate worker immediately
      if (sourceLanguageRef.current !== 'auto') {
        initTranslateWorker(sourceLanguageRef.current, targetLanguageRef.current);
      }

      decodeAudio(file)
        .then((audio) => {
          whisperWorker.postMessage({type: 'start', payload: {audio}}, [audio.buffer]);
        })
        .catch((err: unknown) => {
          setState((prev) => ({
            ...prev,
            status: 'error',
            error: err instanceof Error ? err.message : 'Failed to decode audio',
          }));
          terminateWorkers();
        });
    },
    [terminateWorkers, handleWhisperMessage, handleTranslateMessage, initTranslateWorker],
  );

  const handleSourceLanguageChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      sourceLanguageRef.current = e.target.value;
      setState((prev) => ({...prev}));
    },
    [],
  );

  return (
    <main>
      <div aria-live="polite" role="status">
        {state.status}
      </div>

      {state.error !== null && <p role="alert">{state.error}</p>}

      <label htmlFor="source-language">Source language</label>
      <select
        id="source-language"
        defaultValue="auto"
        onChange={handleSourceLanguageChange}
      >
        <option value="auto">Auto-detect</option>
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </select>

      <DropZone onFileDrop={handleFileDrop} />

      <ul>
        {state.segments.map((seg) => (
          <li key={`${seg.start}-${seg.end}`}>
            <span>{seg.translated}</span>
          </li>
        ))}
      </ul>
    </main>
  );
}