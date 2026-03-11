import WhisperWorker from '../workers/whisper.worker?worker';
import TranslateWorker from '../workers/translate.worker?worker';

export const createWhisperWorker = (): Worker => new WhisperWorker();
export const createTranslateWorker = (): Worker => new TranslateWorker();