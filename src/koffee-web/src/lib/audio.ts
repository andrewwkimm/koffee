export const decodeAudio = async (file: File): Promise<Float32Array> => {
  const arrayBuffer = await file.arrayBuffer();
  // 16kHz required by Whisper
  const audioContext = new AudioContext({sampleRate: 16000});
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  // Take first channel — Whisper expects mono
  return audioBuffer.getChannelData(0);
};