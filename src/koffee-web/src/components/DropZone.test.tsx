import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { DropZone } from "./DropZone";

const makeFile = (name: string, type: string) =>
  new File(["content"], name, { type });

const LABEL_TEXT = "Drop a video file here or click to select";

const getDropzone = () => screen.getByTestId("dropzone");
const getInput = () => screen.getByLabelText(LABEL_TEXT);

describe("DropZone", () => {
  let onFileDrop: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onFileDrop = vi.fn();
    render(<DropZone onFileDrop={onFileDrop} />);
  });

  it("calls onFileDrop with file when valid video is selected via input", async () => {
    await userEvent.upload(getInput(), makeFile("video.mp4", "video/mp4"));

    expect(onFileDrop).toHaveBeenCalledOnce();
    expect(onFileDrop).toHaveBeenCalledWith(
      expect.objectContaining({ name: "video.mp4" }),
    );
  });

  it("calls onFileDrop with file when valid video is dropped", () => {
    fireEvent.dragEnter(getDropzone());
    fireEvent.dragOver(getDropzone());
    fireEvent.drop(getDropzone(), {
      dataTransfer: { files: [makeFile("video.mp4", "video/mp4")] },
    });

    expect(onFileDrop).toHaveBeenCalledOnce();
    expect(onFileDrop).toHaveBeenCalledWith(
      expect.objectContaining({ name: "video.mp4" }),
    );
  });

  it("shows error and does not call onFileDrop for non-video file selected via input", async () => {
    await userEvent.upload(getInput(), makeFile("doc.pdf", "application/pdf"));

    expect(onFileDrop).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Only video files are supported.",
    );
  });

  it("shows error and does not call onFileDrop for non-video file dropped", () => {
    fireEvent.dragEnter(getDropzone());
    fireEvent.drop(getDropzone(), {
      dataTransfer: { files: [makeFile("doc.pdf", "application/pdf")] },
    });

    expect(onFileDrop).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Only video files are supported.",
    );
  });

  it("shows error and does not call onFileDrop when multiple files are selected via input", async () => {
    fireEvent.change(getInput(), {
      target: {
        files: [makeFile("a.mp4", "video/mp4"), makeFile("b.mp4", "video/mp4")],
      },
    });

    expect(onFileDrop).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Drop one file at a time.",
    );
  });

  it("shows error and does not call onFileDrop when file has no MIME type", async () => {
    await userEvent.upload(getInput(), makeFile("video.mp4", ""));

    expect(onFileDrop).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not detect file type. Please try again.",
    );
  });

  it("clears error when a valid file is selected after an invalid one", async () => {
    await userEvent.upload(getInput(), makeFile("doc.pdf", "application/pdf"));
    expect(await screen.findByRole("alert")).toBeInTheDocument();

    await userEvent.upload(getInput(), makeFile("video.mp4", "video/mp4"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(onFileDrop).toHaveBeenCalledOnce();
  });

  it("maintains dragging state when dragging over child elements", () => {
    const dropzone = getDropzone();
    const input = getInput();

    fireEvent.dragEnter(dropzone);
    expect(dropzone).toHaveClass("dropzone--dragging");

    fireEvent.dragEnter(input);
    fireEvent.dragLeave(dropzone);
    expect(dropzone).toHaveClass("dropzone--dragging");

    fireEvent.dragLeave(input);
    expect(dropzone).not.toHaveClass("dropzone--dragging");
  });
});
