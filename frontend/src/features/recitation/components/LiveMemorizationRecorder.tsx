import { useEffect, useRef, useState } from "react";
import {
  analyzeLiveCorrectionChunk,
  finalizeLiveSession,
  startLiveSession,
  type LiveCorrectionResponse,
} from "../api/audio";

interface Props {
  surahNumber: number;
  ayahNumber: number;
  onFeedback: (result: LiveCorrectionResponse) => void;
  onFinalized: (recitationSessionId: string) => void;
}

export function LiveMemorizationRecorder({
  surahNumber,
  ayahNumber,
  onFeedback,
  onFinalized,
}: Props) {
  const [phase, setPhase] = useState<
    "idle" | "starting" | "recording" | "processing" | "finalizing" | "retry" | "done"
  >("idle");
  const [error, setError] = useState("");

  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const sessionId = useRef<string | null>(null);
  const cursor = useRef(0);
  const chunkIndex = useRef(0);
  const failedChunk = useRef<Blob | null>(null);
  const pendingChunks = useRef<Blob[]>([]);
  const processingQueue = useRef(false);
  const recordingFinished = useRef(false);
  const queueError = useRef(false);
  const verseCompleted = useRef(false);
  const MAX_PENDING_CHUNKS = 10;
  const stopping = useRef(false);
  const generation = useRef(0);
  const busy = useRef(false);
  const mounted = useRef(true);
  const feedbackRef = useRef(onFeedback);
  const finalizedRef = useRef(onFinalized);

  useEffect(() => {
    feedbackRef.current = onFeedback;
    finalizedRef.current = onFinalized;
  }, [onFeedback, onFinalized]);

  function releaseMicrophone() {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  }

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      generation.current += 1;
      if (recorder.current?.state === "recording") {
        recorder.current.onstop = null;
        recorder.current.stop();
      }
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function finalize(run: number) {
    if (!sessionId.current || busy.current || run !== generation.current) return;
    busy.current = true;
    releaseMicrophone();
    setPhase("finalizing");

    try {
      const result = await finalizeLiveSession(sessionId.current);
      if (!mounted.current || run !== generation.current) return;
      sessionId.current = null;
      setPhase("done");
      finalizedRef.current(result.recitation_session_id);
    } catch (err) {
      if (!mounted.current || run !== generation.current) return;
      setError(err instanceof Error ? err.message : "تعذر حفظ التلاوة.");
      setPhase("retry");
    } finally {
      busy.current = false;
    }
  }

  async function retryFailedChunk() {
    if (!sessionId.current || processingQueue.current || busy.current) return;

    failedChunk.current = null;
    queueError.current = false;
    setError("");
    setPhase("processing");

    if (pendingChunks.current.length > 0) {
      await processPendingChunks(generation.current);
    } else if (recordingFinished.current) {
      await finalize(generation.current);
    }
  }

  async function processPendingChunks(run: number) {
    if (processingQueue.current || queueError.current) return;
    processingQueue.current = true;

    try {
      while (pendingChunks.current.length > 0) {
        if (!mounted.current || run !== generation.current) return;

        const blob = pendingChunks.current[0];

        try {
          const result = await analyzeLiveCorrectionChunk(
            blob,
            surahNumber,
            ayahNumber,
            cursor.current,
            sessionId.current ?? undefined,
            chunkIndex.current,
          );

          if (!mounted.current || run !== generation.current) return;

          pendingChunks.current.shift();
          feedbackRef.current(result);
          cursor.current = result.next_word_index;
          chunkIndex.current += 1;

          if (!result.has_more_words) {
            verseCompleted.current = true;
            stopping.current = true;
            pendingChunks.current = [];

            const active = recorder.current;
            if (active?.state === "recording") {
              active.stop();
            } else {
              recordingFinished.current = true;
              releaseMicrophone();
            }

            break;
          }
        } catch (err) {
          if (!mounted.current || run !== generation.current) return;
          queueError.current = true;
          failedChunk.current = blob;
          stopping.current = true;

          const active = recorder.current;
          if (active?.state === "recording") {
            active.stop();
          } else {
            recordingFinished.current = true;
            releaseMicrophone();
          }

          setError(err instanceof Error ? err.message : "تعذر تحليل الصوت.");
          setPhase("retry");
          return;
        }
      }
    } finally {
      processingQueue.current = false;
    }

    if (
      recordingFinished.current &&
      !queueError.current &&
      pendingChunks.current.length === 0
    ) {
      await finalize(run);
    }
  }

  function stop() {
    if (stopping.current) return;
    stopping.current = true;
    setPhase("processing");

    const current = recorder.current;
    if (current?.state === "recording") {
      current.stop();
    } else {
      recordingFinished.current = true;
      void processPendingChunks(generation.current);
    }
  }

  async function start() {
    if (busy.current || sessionId.current) return;
    busy.current = true;
    setError("");
    setPhase("starting");
    stopping.current = false;
    cursor.current = 0;
    chunkIndex.current = 0;
    failedChunk.current = null;
    pendingChunks.current = [];
    processingQueue.current = false;
    recordingFinished.current = false;
    queueError.current = false;
    verseCompleted.current = false;
    const run = ++generation.current;
    let microphone: MediaStream | null = null;

    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
        throw new Error("المتصفح لا يدعم التسجيل الصوتي.");
      }

      const mime = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus"]
        .find((type) => MediaRecorder.isTypeSupported(type));

      if (!mime) throw new Error("المتصفح لا يدعم WebM أو Ogg.");

      microphone = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current || run !== generation.current) {
        microphone.getTracks().forEach((track) => track.stop());
        return;
      }

      const live = await startLiveSession(surahNumber, ayahNumber);
      if (!mounted.current || run !== generation.current) {
        microphone.getTracks().forEach((track) => track.stop());
        return;
      }

      sessionId.current = live.session_id;
      if (!microphone) {
        throw new Error("تعذر الوصول للميكروفون.");
      }
      const recordingStream = microphone;
      stream.current = recordingStream;
      setPhase("recording");

      const recordNext = () => {
        if (!mounted.current || run !== generation.current || stopping.current) return;

        const chunks: Blob[] = [];
        const current = new MediaRecorder(recordingStream, { mimeType: mime });
        recorder.current = current;

        current.ondataavailable = (event) => {
          if (event.data.size) chunks.push(event.data);
        };

        current.onerror = () => {
          if (!mounted.current || run !== generation.current) return;

          queueError.current = true;
          stopping.current = true;

          if (current.state === "recording") {
            current.stop();
          } else {
            recordingFinished.current = true;
            releaseMicrophone();
          }

          setError("حدث خطأ أثناء التسجيل. يمكنك إعادة محاولة حفظ المقاطع المسجلة.");
          setPhase("retry");
        };

        current.onstop = () => {
          if (!mounted.current || run !== generation.current) return;

          const blob = new Blob(chunks, { type: mime });

          if (blob.size && !verseCompleted.current) {
            pendingChunks.current.push(blob);
          }

          if (
            !stopping.current &&
            pendingChunks.current.length < MAX_PENDING_CHUNKS
          ) {
            recordNext();
          } else {
            stopping.current = true;
            recordingFinished.current = true;
            releaseMicrophone();

            if (pendingChunks.current.length >= MAX_PENDING_CHUNKS) {
              setError("تم إيقاف التسجيل لأن معالجة الصوت أبطأ من التسجيل.");
            }

            if (!queueError.current) {
              setPhase("processing");
            }
          }

          if (!queueError.current) {
            void processPendingChunks(run);
          }
        };

        current.start();
        window.setTimeout(() => {
          if (current.state === "recording") current.stop();
        }, 3000);
      };

      recordNext();
    } catch (err) {
      microphone?.getTracks().forEach((track) => track.stop());
      if (mounted.current && run === generation.current) {
        setError(err instanceof Error ? err.message : "تعذر بدء التسجيل.");
        setPhase("idle");
      }
    } finally {
      busy.current = false;
    }
  }

  return (
    <section dir="rtl" aria-label="التسميع المباشر">
      <h3>التسميع بالتصحيح المباشر</h3>
      <p>تحليل مقاطع قصيرة من التلاوة، والنتائج مبدئية.</p>

      {phase === "idle" && (
        <button type="button" onClick={() => void start()}>
          بدء التسميع
        </button>
      )}

      {phase === "recording" && (
        <button type="button" onClick={stop}>
          إيقاف التسميع وحفظه
        </button>
      )}

      {phase === "retry" && (
        <button type="button" onClick={() => {
            void retryFailedChunk();
          }}>
          إعادة محاولة حفظ التلاوة
        </button>
      )}

      {phase === "starting" && <p role="status">جارٍ بدء الجلسة...</p>}
      {phase === "processing" && <p role="status">جارٍ تحليل آخر مقطع...</p>}
      {phase === "finalizing" && <p role="status">جارٍ حفظ التلاوة...</p>}
      {phase === "done" && <p role="status">تم حفظ التلاوة بنجاح.</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
