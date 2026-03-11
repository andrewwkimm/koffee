import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { Segment, TranslatedSegment } from "./lib/types";

// --- Mock Workers ---

class MockWorker {
  onmessage: ((e: MessageEvent) => void) | null = null;
  postMessage = vi.fn();
  terminate = vi.fn();

  emit(data: unknown) {
    this.onmessage?.(new MessageEvent("message", { data }));
  }
}

let mockWhisperWorker: MockWorker;
let mockTranslateWorker: MockWorker;

vi.mock("./lib/workerFactory", () => ({
  createWhisperWorker: vi.fn(() => {
    mockWhisperWorker = new MockWorker();
    return mockWhisperWorker;
  }),
  createTranslateWorker: vi.fn(() => {
    mockTranslateWorker = new MockWorker();
    return mockTranslateWorker;
  }),
}));

// --- Helpers ---

const makeFile = (name: string, type: string) =>
  new File(["content"], name, { type });

const dropFile = async (file: File) =>
  userEvent.upload(
    screen.getByLabelText("Drop a video file here or click to select"),
    file,
  );

const validVideo = makeFile("video.mp4", "video/mp4");

const makeSegment = (text: string, start: number, end: number): Segment => ({
  text,
  start,
  end,
});

const makeTranslatedSegment = (
  original: string,
  translated: string,
  start: number,
  end: number,
): TranslatedSegment => ({ original, translated, start, end });

// --- Tests ---

describe("App", () => {
  it("initialises both workers when a valid file is dropped", async () => {
    render(<App />);
    await dropFile(validVideo);

    expect(mockWhisperWorker).toBeDefined();
    expect(mockTranslateWorker).toBeDefined();
  });

  it("forwards whisper segment to translate worker", async () => {
    render(<App />);
    await dropFile(validVideo);

    const segment = makeSegment("Hello world", 0, 2.5);

    act(() => {
      mockWhisperWorker.emit({ type: "segment", payload: segment });
    });

    expect(mockTranslateWorker.postMessage).toHaveBeenCalledWith({
      type: "segment",
      payload: segment,
    });
  });

  it("accumulates translated segments in order", async () => {
    render(<App />);
    await dropFile(validVideo);

    const first = makeTranslatedSegment("Hello", "Hola", 0, 2.5);
    const second = makeTranslatedSegment("World", "Mundo", 2.5, 5.0);

    act(() => {
      mockTranslateWorker.emit({ type: "segment", payload: first });
      mockTranslateWorker.emit({ type: "segment", payload: second });
    });

    expect(screen.getByText("Hola")).toBeInTheDocument();
    expect(screen.getByText("Mundo")).toBeInTheDocument();
  });

  it("sends init to translate worker with detected language when sourceLanguage is auto", async () => {
    render(<App />);
    await dropFile(validVideo);

    // Translate worker exists but has not received init yet —
    // App.tsx is waiting for whisper to report the detected language
    expect(mockTranslateWorker.postMessage).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: "init" }),
    );

    act(() => {
      mockWhisperWorker.emit({ type: "done", payload: { language: "es" } });
    });

    expect(mockTranslateWorker.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "init",
        payload: expect.objectContaining({ sourceLanguage: "es" }),
      }),
    );
  });

  it("sends init to translate worker immediately with user-selected source language", async () => {
    render(<App />);

    await userEvent.selectOptions(
      screen.getByLabelText("Source language"),
      "fr",
    );
    await dropFile(validVideo);

    // sourceLanguage is known at drop time — init is sent immediately
    expect(mockTranslateWorker.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "init",
        payload: expect.objectContaining({ sourceLanguage: "fr" }),
      }),
    );
  });

  it("terminates existing workers and creates fresh ones on second file drop", async () => {
    render(<App />);
    await dropFile(validVideo);

    const firstWhisper = mockWhisperWorker;
    const firstTranslate = mockTranslateWorker;

    await dropFile(makeFile("sample_video.mp4", "video/mp4"));

    expect(firstWhisper.terminate).toHaveBeenCalledOnce();
    expect(firstTranslate.terminate).toHaveBeenCalledOnce();
    expect(mockWhisperWorker).not.toBe(firstWhisper);
    expect(mockTranslateWorker).not.toBe(firstTranslate);
  });

  it("continues pipeline on non-fatal translate error", async () => {
    render(<App />);
    await dropFile(validVideo);

    act(() => {
      mockWhisperWorker.emit({
        type: "segment",
        payload: makeSegment("Hello", 0, 2.5),
      });
      mockTranslateWorker.emit({
        type: "error",
        payload: {
          code: "EMPTY_TRANSLATION",
          message: "Empty result",
          fatal: false,
        },
      });
    });

    expect(mockWhisperWorker.terminate).not.toHaveBeenCalled();
    expect(mockTranslateWorker.terminate).not.toHaveBeenCalled();
  });

  it("terminates existing workers and creates fresh ones on second file drop", async () => {
    render(<App />);
    await dropFile(validVideo);

    const firstWhisper = mockWhisperWorker;
    const firstTranslate = mockTranslateWorker;

    await dropFile(validVideo);

    expect(firstWhisper.terminate).toHaveBeenCalledOnce();
    expect(firstTranslate.terminate).toHaveBeenCalledOnce();
    expect(mockWhisperWorker).not.toBe(firstWhisper);
    expect(mockTranslateWorker).not.toBe(firstTranslate);
  });

  it("sets status to error on fatal error", async () => {
    render(<App />);
    await dropFile(validVideo);

    act(() => {
      mockWhisperWorker.emit({
        type: "error",
        payload: {
          code: "TRANSCRIPTION_FAILED",
          message: "Failed",
          fatal: true,
        },
      });
    });

    expect(screen.getByRole("status")).toHaveTextContent("error");
  });
});
