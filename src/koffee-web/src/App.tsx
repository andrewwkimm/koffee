import {createWhisperWorker, createTranslateWorker} from './lib/workerFactory';
import {useState, useRef, useCallback} from 'react';
import {DropZone} from './components/DropZone';
import type {
  Segment,
  TranslatedSegment,
  WhisperMessage,
  TranslateMessage,
  TranslateWorkerInbound,
} from './lib/types';

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

  const whisperWorkerRef = useRef<Worker | null>(null);
  const translateWorkerRef = useRef<Worker | null>(null);

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

  const handleTranslateMessage = useCallback(
    (e: MessageEvent<TranslateMessage>) => {
      const msg = e.data;

      if (msg.type === 'segment') {
        setState((prev) => ({
          ...prev,
          segments: [...prev.segments, msg.payload],
        }));
        return;
      }

      if (msg.type === 'done') {
        setState((prev) => ({...prev, status: 'done'}));
        terminateWorkers();
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
    [terminateWorkers],
  );

  const handleWhisperMessage = useCallback(
    (e: MessageEvent<WhisperMessage>) => {
      const msg = e.data;

      if (msg.type === 'segment') {
        const payload: TranslateWorkerInbound = {
          type: 'segment',
          payload: msg.payload as Segment,
        };
        translateWorkerRef.current?.postMessage(payload);
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

      whisperWorker.postMessage({type: 'start', payload: {file}});
    },
    [terminateWorkers, handleWhisperMessage, handleTranslateMessage, initTranslateWorker],
  );

  const handleSourceLanguageChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      sourceLanguageRef.current = e.target.value;
      // Force re-render so UI reflects selection
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
        <option value="en">English</option>
        <option value="es">Spanish</option>
        <option value="fr">French</option>
        <option value="de">German</option>
        <option value="ja">Japanese</option>
        <option value="zh">Chinese</option>
      </select>

      <DropZone onFileDrop={handleFileDrop} />

      <ul>
        {state.segments.map((seg, i) => (
          <li key={i}>
            <span>{seg.translated}</span>
          </li>
        ))}
      </ul>
    </main>
  );
}