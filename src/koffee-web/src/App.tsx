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

type PipelineStatus = 'idle' | 'transcribing' | 'translating' | 'muxing' | 'done' | 'error';

interface AppState {
  file: File | null;
  segments: TranslatedSegment[];
  status: PipelineStatus;
  error: string | null;
  sourceLanguage: string;
}

const INITIAL_STATE: AppState = {
  file: null,
  segments: [],
  status: 'idle',
  error: null,
  sourceLanguage: 'auto',
};

export default function App() {
  const [state, setState] = useState<AppState>(INITIAL_STATE);

  // Keep ref in sync with state for use in worker callbacks
  const sourceLanguageRef = useRef<string>('auto');
  const targetLanguageRef = useRef<string>('en');
  const segmentsRef = useRef<TranslatedSegment[]>([]);
  const fileRef = useRef<File | null>(null);
  const translateReadyRef = useRef(false);
  const segmentBufferRef = useRef<Segment[]>([]);
  const whisperDoneRef = useRef(false);
  const whisperWorkerRef = useRef<Worker | null>(null);
  const translateWorkerRef = useRef<Worker | null>(null);

  useEffect(() => {
    initFFmpeg().catch((err: unknown) => {
      console.error('[ffmpeg] failed to load:', err);
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
      // If source and target are the same, skip translation — pass segments through directly
      if (sourceLanguage === targetLanguage) {
        console.log('[translate] same language, skipping translation');
        // Convert buffered segments to TranslatedSegments directly
        const passthrough: TranslatedSegment[] = segmentBufferRef.current.map((seg) => ({
          original: seg.text,
          translated: seg.text,
          start: seg.start,
          end: seg.end,
        }));
        segmentBufferRef.current = [];
        segmentsRef.current = passthrough;
        setState((prev) => ({...prev, segments: passthrough, status: 'muxing'}));

        muxSubtitles(fileRef.current!, passthrough)
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
            console.error('[mux] failed:', err);
            setState((prev) => ({
              ...prev,
              status: 'error',
              error: err instanceof Error ? err.message : String(err),
            }));
          })
          .finally(() => {
            terminateWorkers();
          });
        return;
      }

      console.log('[translate] sending init with:', sourceLanguage, targetLanguage);
      const payload: TranslateWorkerInbound = {
        type: 'init',
        payload: {sourceLanguage, targetLanguage},
      };
      translateWorkerRef.current?.postMessage(payload);
    },
    [terminateWorkers],
  );

  const flushSegmentBuffer = useCallback((sendDone: boolean = false) => {
    console.log('[translate] flushing buffer, segments:', segmentBufferRef.current.length);
    for (const segment of segmentBufferRef.current) {
      translateWorkerRef.current?.postMessage({
        type: 'segment',
        payload: segment,
      });
    }
    segmentBufferRef.current = [];

    if (sendDone) {
      console.log('[translate] sending done to translate worker');
      translateWorkerRef.current?.postMessage({type: 'done'});
    }
  }, []);

  const handleTranslateMessage = useCallback(
    (e: MessageEvent<TranslateMessage>) => {
      const msg = e.data;
      console.log('[translate] message received:', msg.type);

      if (msg.type === 'ready') {
        console.log('[translate] worker ready, flushing buffer');
        translateReadyRef.current = true;
        flushSegmentBuffer(whisperDoneRef.current);
        return;
      }

      if (msg.type === 'segment') {
        segmentsRef.current = [...segmentsRef.current, msg.payload];
        setState((prev) => ({...prev, segments: segmentsRef.current}));
        return;
      }

      if (msg.type === 'done') {
        setState((prev) => ({...prev, status: 'muxing'}));

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
            console.error('[mux] failed:', err);
            setState((prev) => ({
              ...prev,
              status: 'error',
              error: err instanceof Error ? err.message : String(err),
            }));
          })
          .finally(() => {
            terminateWorkers();
          });

        return;
      }

      if (msg.type === 'error') {
        console.log('[translate] error:', msg.payload);
        if (msg.payload.fatal) {
          setState((prev) => ({
            ...prev,
            status: 'error',
            error: msg.payload.message,
          }));
          terminateWorkers();
          return;
        }
      }
    },
    [terminateWorkers, flushSegmentBuffer],
  );

  const handleWhisperMessage = useCallback(
    (e: MessageEvent<WhisperMessage>) => {
      const msg = e.data;
      console.log('[whisper] message received:', msg.type);

      if (msg.type === 'segment') {
        const segment = msg.payload as Segment;

        if (translateReadyRef.current) {
          translateWorkerRef.current?.postMessage({type: 'segment', payload: segment});
        } else {
          console.log('[whisper] buffering segment, translate not ready yet');
          segmentBufferRef.current = [...segmentBufferRef.current, segment];
        }
        return;
      }

      if (msg.type === 'done') {
        console.log('[whisper] done, detected language:', msg.payload.language);
        console.log('[whisper] sourceLanguageRef:', sourceLanguageRef.current);

        const sourceLanguage =
          sourceLanguageRef.current === 'auto'
            ? msg.payload.language
            : sourceLanguageRef.current;

        sourceLanguageRef.current = sourceLanguage;
        whisperDoneRef.current = true;
        setState((prev) => ({...prev, status: 'translating'}));

        if (translateReadyRef.current) {
          flushSegmentBuffer(true);
        } else {
          initTranslateWorker(sourceLanguage, targetLanguageRef.current);
        }
        return;
      }

      if (msg.type === 'error' && msg.payload.fatal) {
        console.log('[whisper] fatal error:', msg.payload);
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: msg.payload.message,
        }));
        terminateWorkers();
      }
    },
    [initTranslateWorker, terminateWorkers, flushSegmentBuffer],
  );

  const handleFileDrop = useCallback(
    (file: File) => {
      console.log('[app] file dropped:', file.name, 'source lang:', sourceLanguageRef.current);
      terminateWorkers();

      segmentsRef.current = [];
      fileRef.current = file;
      translateReadyRef.current = false;
      segmentBufferRef.current = [];
      whisperDoneRef.current = false;

      setState((prev) => ({...INITIAL_STATE, file, status: 'transcribing', sourceLanguage: prev.sourceLanguage}));

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
          console.log('[app] audio decoded, starting whisper, lang hint:', sourceLanguageRef.current);
          // Pass language hint to whisper if user pre-selected
          const langHint = sourceLanguageRef.current !== 'auto' ? sourceLanguageRef.current : undefined;
          whisperWorker.postMessage({type: 'start', payload: {audio, language: langHint}}, [audio.buffer]);
        })
        .catch((err: unknown) => {
          console.error('[app] audio decode failed:', err);
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
      const value = e.target.value;
      console.log('[app] source language changed to:', value);
      sourceLanguageRef.current = value;
      setState((prev) => ({...prev, sourceLanguage: value}));
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
        value={state.sourceLanguage}
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