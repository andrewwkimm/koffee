import { useState, useCallback } from 'react';

interface DropZoneProps {
  onFileDrop: (file: File) => void;
}

type DropError = 'invalid-type' | 'multiple-files' | 'no-mime-type';

const ERROR_MESSAGES: Record<DropError, string> = {
  'invalid-type': 'Only video files are supported.',
  'multiple-files': 'Drop one file at a time.',
  'no-mime-type': 'Could not detect file type. Please try again.',
};

const validateFile = (files: FileList): { file: File } | { error: DropError } => {
  if (files.length > 1) return { error: 'multiple-files' };

  const file = files[0];

  if (!file.type) return { error: 'no-mime-type' };
  if (!file.type.startsWith('video/')) return { error: 'invalid-type' };

  return { file };
};

export const DropZone = ({ onFileDrop }: DropZoneProps) => {
  const [error, setError] = useState<DropError | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = useCallback(
    (files: FileList) => {
      const result = validateFile(files);

      if ('error' in result) {
        setError(result.error);
        return;
      }

      setError(null);
      onFileDrop(result.file);
    },
    [onFileDrop],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) handleFiles(e.target.files);
    },
    [handleFiles],
  );

  return (
    <div
      onDragEnter={() => { setIsDragging(true); setError(null); }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={isDragging ? 'dropzone dropzone--dragging' : 'dropzone'}
    >
      <label htmlFor="dropzone-input">
        Drop a video file here or click to select
      </label>
      <input
        id="dropzone-input"
        type="file"
        accept="video/*"
        onChange={handleChange}
      />
      {error && <p role="alert">{ERROR_MESSAGES[error]}</p>}
    </div>
  );
};