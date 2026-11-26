import { VolumeIcon, PauseIcon } from "../icons.js";

const { useEffect, useRef, useState } = window.React;
const html = window.htm.bind(window.React.createElement);

export function AudioReminderPlayer({ ruleId, lang, voiceScripts, t, title }) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progressPct, setProgressPct] = useState(0);
  const [modeNote, setModeNote] = useState("");

  const meta = voiceScripts?.[ruleId]?.languages?.[lang] || null;

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setIsPlaying(false);
    setProgressPct(0);
    setModeNote("");
  }, [ruleId, lang]);

  useEffect(() => {
    return () => {
      if (window.speechSynthesis) window.speechSynthesis.cancel();
    };
  }, []);

  if (!meta) return null;

  function speakFallback() {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(meta.text);
    utter.lang = meta.locale || "en-IN";
    utter.rate = 0.88;
    utter.onend = () => {
      setIsPlaying(false);
      setProgressPct(100);
    };
    setIsPlaying(true);
    setProgressPct(35);
    setModeNote(`${meta.locale} speech synthesis`);
    window.speechSynthesis.speak(utter);
  }

  function togglePlayback() {
    if (isPlaying) {
      if (audioRef.current) audioRef.current.pause();
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }

    const audio = audioRef.current;
    if (audio) {
      audio.src = `./${meta.audio_rel_path}`;
      audio
        .play()
        .then(() => {
          setIsPlaying(true);
          setModeNote(`${meta.voice_name} (${meta.rate})`);
        })
        .catch(() => {
          speakFallback();
        });
    } else {
      speakFallback();
    }
  }

  return html`
    <div class="audio-box">
      <div class="screen-header" style=${{ alignItems: "center" }}>
        <div>
          <div class="card-title" style=${{ fontSize: "var(--text-base)" }}>
            <span class="icon-box"><${VolumeIcon} /></span>
            <span>${title || t.timetable.voice_section}</span>
          </div>
          <div class="stat-meta mono">
            ${meta.voice_name} | ${meta.estimated_seconds}s
          </div>
        </div>
        <button type="button" class="btn btn-primary" onClick=${togglePlayback}>
          <span class="icon-box" style=${{ color: "#ffffff" }}>
            ${isPlaying ? html`<${PauseIcon} />` : html`<${VolumeIcon} />`}
          </span>
          <span>${isPlaying ? t.timetable.pause_voice : t.timetable.play_voice}</span>
        </button>
      </div>

      <audio
        ref=${audioRef}
        preload="none"
        onTimeUpdate=${(e) => {
          const el = e.currentTarget;
          if (el.duration > 0) {
            setProgressPct(Math.round((el.currentTime / el.duration) * 100));
          }
        }}
        onEnded=${() => {
          setIsPlaying(false);
          setProgressPct(100);
        }}
        onError=${() => {
          if (isPlaying) speakFallback();
        }}
      />

      <div class="audio-progress" aria-hidden="true">
        <div class="audio-progress-fill" style=${{ width: `${progressPct}%` }} />
      </div>

      <div>
        <div class="field-label" style=${{ marginBottom: "4px" }}>${t.timetable.script_label}</div>
        <p style=${{ margin: 0, fontSize: "var(--text-sm)", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          ${meta.text}
        </p>
      </div>
      ${modeNote ? html`<div class="stat-meta mono">${modeNote}</div>` : null}
    </div>
  `;
}
