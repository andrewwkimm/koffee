import {useState, useCallback, useRef} from 'react';
import clsx from 'clsx';

interface DropZoneProps {
  onFileDrop: (file: File) => void;
}

type DropError = 'invalid-type' | 'multiple-files' | 'no-mime-type';

const ERROR_MESSAGES: Record<DropError, string> = {
  'invalid-type': 'Only video files are supported.',
  'multiple-files': 'Drop one file at a time.',
  'no-mime-type': 'Could not detect file type. Please try again.',
};

const validateFile = (files: FileList): {file: File} | {error: DropError} => {
  if (files.length > 1) return {error: 'multiple-files'};

  const file = files[0];

  if (!file) return {error: 'no-mime-type'};
  if (!file.type) return {error: 'no-mime-type'};
  if (!file.type.startsWith('video/')) return {error: 'invalid-type'};

  return {file};
};

export const DropZone = ({onFileDrop}: DropZoneProps) => {
  const [error, setError] = useState<DropError | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);

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

  const handleDragEnter = useCallback(() => {
    dragCounter.current += 1;
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      dragCounter.current = 0;
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
      data-testid="dropzone"
      role="region"
      aria-label="Video file drop zone"
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={clsx('dropzone', {'dropzone--dragging': isDragging})}
    >
      <label htmlFor="dropzone-input">
        Drop a video file here or click to select
      </label>

    {/* `multiple` intentionally omitted: the picker enforces single-file selection.
        Drag-and-drop ignores this attribute, so validateFile is the real gate for both paths.
        `accept` intentionally omitted: validateFile is the single source of truth for
        file type validation. The attribute is a UX hint only and interferes with test reliability. */}
    <input
      id="dropzone-input"
      type="file"
      onChange={handleChange}
    />

      {error !== null && <p role="alert">{ERROR_MESSAGES[error]}</p>}
    </div>
  );
};