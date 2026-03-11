import {render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {DropZone} from './DropZone';

const makeFile = (name: string, type: string) => new File(['content'], name, {type});

describe('DropZone', () => {
  it('calls onFileDrop with file when valid video is dropped', async () => {
    const onFileDrop = vi.fn();
    render(<DropZone onFileDrop={onFileDrop} />);

    await userEvent.upload(screen.getByTestId('dropzone-input'), makeFile('video.mp4', 'video/mp4'));

    expect(onFileDrop).toHaveBeenCalledOnce();
    expect(onFileDrop).toHaveBeenCalledWith(expect.objectContaining({name: 'video.mp4'}));
  });

  it('shows error and does not call onFileDrop for non-video file', async () => {
    const onFileDrop = vi.fn();
    render(<DropZone onFileDrop={onFileDrop} />);

    await userEvent.upload(screen.getByTestId('dropzone-input'), makeFile('doc.pdf', 'application/pdf'));

    expect(onFileDrop).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('shows error and does not call onFileDrop when multiple files are dropped', async () => {
    const onFileDrop = vi.fn();
    render(<DropZone onFileDrop={onFileDrop} />);

    // TODO: multifile support
    await userEvent.upload(screen.getByTestId('dropzone-input'), [
      makeFile('a.mp4', 'video/mp4'),
      makeFile('b.mp4', 'video/mp4'),
    ]);

    expect(onFileDrop).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('shows error and does not call onFileDrop when file has no MIME type', async () => {
    const onFileDrop = vi.fn();
    render(<DropZone onFileDrop={onFileDrop} />);

    await userEvent.upload(screen.getByTestId('dropzone-input'), makeFile('video.mp4', ''));

    expect(onFileDrop).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});