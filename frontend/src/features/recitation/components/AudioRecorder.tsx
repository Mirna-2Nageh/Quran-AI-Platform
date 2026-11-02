import {
  analyzeRecitationAudio,
  type AudioAnalysisResponse,
  type WordTiming,
} from "../api/audio";
import { useEffect, useRef, useState } from "react";
import { Mic, Square, RotateCcw } from "lucide-react";

type RecorderStatus = "idle" | "recording" | "recorded";

interface AudioRecorderProps {
  expectedText: string;
  surahNumber: number;
  ayahNumber: number;
  endAyahNumber?: number;
  onAnalysisComplete: (result: AudioAnalysisResponse) => void;
  onRecordingReset: () => void;
}

export function AudioRecorder({
  expectedText,
  surahNumber,
  ayahNumber,
  endAyahNumber = ayahNumber,
  onAnalysisComplete,
  onRecordingReset,
}: AudioRecorderProps) {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analysisSuccess, setAnalysisSuccess] = useState(false);
  const [wordTimings, setWordTimings] = useState<WordTiming[]>([]);
  const [playbackTime, setPlaybackTime] = useState(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const analysisRequestId = useRef(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const urlRef = useRef<string | null>(null);

  function cleanupStream() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  function clearAudio() {
    analysisRequestId.current += 1;
    setUploading(false);
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
    setAudioUrl(null);
    setAudioBlob(null);
    setAnalysisSuccess(false);
    setWordTimings([]);
    setPlaybackTime(0);
  }

  async function startRecording() {
    setError("");

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("المتصفح لا يدعم التسجيل الصوتي.");
      return;
    }

    if (typeof MediaRecorder === "undefined") {
      setError("تسجيل الصوت غير مدعوم في هذا المتصفح.");
      return;
    }

    try {
      clearAudio();
      onRecordingReset();
      chunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      streamRef.current = stream;

      const preferredMimeType = "audio/webm;codecs=opus";

      if (!MediaRecorder.isTypeSupported(preferredMimeType)) {
        cleanupStream();
        setError("المتصفح لا يدعم تسجيل WebM/Opus.");
        return;
      }

      const recorder = new MediaRecorder(stream, {
        mimeType: preferredMimeType,
      });
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        cleanupStream();
        recorderRef.current = null;

        if (blob.size === 0) {
          setError("التسجيل فارغ. حاول مرة أخرى.");
          setStatus("idle");
          return;
        }

        const url = URL.createObjectURL(blob);
        urlRef.current = url;
        setAudioUrl(url);
        setAudioBlob(blob);
        setStatus("recorded");
      };

      recorder.onerror = () => {
        setError("حدث خطأ أثناء تسجيل الصوت.");
        cleanupStream();
        setStatus("idle");
      };

      recorder.start();
      setStatus("recording");
    } catch {
      cleanupStream();
      setError("تعذر الوصول للميكروفون. تحقق من صلاحيات المتصفح.");
      setStatus("idle");
    }
  }

  async function handleUpload() {
    if (!audioBlob || uploading) {
      return;
    }

    const requestId = ++analysisRequestId.current;
    onRecordingReset();
    setUploading(true);
    setError("");
    setAnalysisSuccess(false);
    setWordTimings([]);
    setPlaybackTime(0);

    try {
      const result = await analyzeRecitationAudio(
        audioBlob,
        expectedText,
        surahNumber,
        ayahNumber,
        endAyahNumber,
      );

      if (requestId === analysisRequestId.current) {
        onAnalysisComplete(result);
        setWordTimings(result.word_timings);
        setAnalysisSuccess(true);
      }
    } catch (err) {
      if (requestId === analysisRequestId.current) {
        setError(
          err instanceof Error
            ? err.message
            : "تعذر رفع التسجيل.",
        );
      }
    } finally {
      if (requestId === analysisRequestId.current) {
        setUploading(false);
      }
    }
  }

  function seekToWord(startSeconds: number) {
    const audio = audioRef.current;

    if (
      !audio ||
      !Number.isFinite(startSeconds) ||
      startSeconds < 0 ||
      audio.readyState < HTMLMediaElement.HAVE_METADATA
    ) {
      return;
    }

    if (
      Number.isFinite(audio.duration) &&
      startSeconds > audio.duration
    ) {
      return;
    }

    audio.currentTime = startSeconds;
    setPlaybackTime(startSeconds);
    void audio.play().catch(() => {
      // Browser playback restrictions may require manual play.
    });
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }
  }

  function resetRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }

    clearAudio();
    chunksRef.current = [];
    setStatus("idle");
    setError("");
    onRecordingReset();
  }

  useEffect(() => {
    return () => {
      analysisRequestId.current += 1;
      const recorder = recorderRef.current;

      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        recorder.stop();
      }

      streamRef.current?.getTracks().forEach((track) => track.stop());

      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
      }
    };
  }, []);

  return (
    <section className="audio-recorder">
      <h2>تسجيل التلاوة</h2>

      <p className="muted">
        سجّل تلاوتك، ثم استمع إليها قبل إرسالها للتحليل.
      </p>

      {status === "idle" && (
        <button type="button" onClick={startRecording}>
          <Mic size={18} />
          بدء التسجيل
        </button>
      )}

      {status === "recording" && (
        <div className="recording-actions">
          <p className="recording-indicator">
            ● جاري التسجيل...
          </p>

          <button type="button" onClick={stopRecording}>
            <Square size={18} />
            إيقاف التسجيل
          </button>
        </div>
      )}

      {status === "recorded" && audioUrl && (
        <div className="audio-playback">
          <audio
            ref={audioRef}
            controls
            src={audioUrl}
            onTimeUpdate={(event) =>
              setPlaybackTime(event.currentTarget.currentTime)
            }
            onSeeked={(event) =>
              setPlaybackTime(event.currentTarget.currentTime)
            }
            onEnded={() => setPlaybackTime(0)}
          />

          {analysisSuccess && wordTimings.length > 0 && (
            <div className="recitation-word-timings" dir="rtl">
              <p className="muted">
                متابعة زمنية تقريبية للكلمات التي تعرف عليها النظام،
                وليست تقييمًا للنطق أو التجويد.
              </p>
              <div className="recitation-timed-words" lang="ar">
                {wordTimings.map((item, index) => {
                  const nextStart = wordTimings[index + 1]?.start_seconds;
                  const end = item.end_seconds ?? nextStart;
                  const active =
                    playbackTime >= item.start_seconds &&
                    (end === undefined || playbackTime < end);

                  return (
                    <button
                      type="button"
                      key={`${index}-${item.start_seconds}`}
                      className={active ? "timed-word active" : "timed-word"}
                      onClick={() => seekToWord(item.start_seconds)}
                      aria-label={`استمع من كلمة ${item.word}`}
                      title={`الانتقال إلى ${item.start_seconds.toFixed(2)} ثانية`}
                    >
                      {item.word}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={handleUpload}
            disabled={uploading || !audioBlob}
          >
            {uploading ? "جاري تحليل التلاوة..." : "تحليل التلاوة"}
          </button>

          <button
            type="button"
            onClick={resetRecording}
            disabled={uploading}
          >
            <RotateCcw size={18} />
            إعادة التسجيل
          </button>

          {analysisSuccess && (
            <p role="status">
              اكتمل التعرف على النص ومقارنته بالآيات المختارة.
            </p>
          )}
        </div>
      )}

      {error && <p role="alert" className="form-error">{error}</p>}
    </section>
  );
}
