# -*- coding: utf-8 -*-
"""
Utility functions shared across speaking skill evaluation modules.
Supports Unicode Tamil text processing
"""
import numpy as np
import subprocess
import os
import shutil
from typing import Optional


def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, x))


def get_ffmpeg_exe_path() -> Optional[str]:
    """
    Returns absolute path to ffmpeg executable.
    Prefer system ffmpeg, else use imageio-ffmpeg bundled binary.
    """
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def load_audio_array(audio_path: str, sr: int = 16000) -> np.ndarray:
    """
    Decode audio into float32 mono waveform using ffmpeg (absolute path if needed).
    This avoids Whisper's internal 'ffmpeg' PATH lookup on Windows.
    """
    ffmpeg_exe = get_ffmpeg_exe_path()
    if not ffmpeg_exe:
        raise FileNotFoundError("ffmpeg executable not found (install ffmpeg or imageio-ffmpeg)")

    cmd = [
        ffmpeg_exe,
        "-nostdin",
        "-threads",
        "0",
        "-i",
        audio_path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sr),
        "-",
    ]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    audio = np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
    return audio


def audio_duration_sec_from_path(audio_path: str) -> float:
    """Get audio duration in seconds from file path."""
    audio = load_audio_array(audio_path, sr=16000)
    sr = 16000
    if audio.size == 0:
        return 0.0
    return float(audio.size) / float(sr)


def estimate_speech_activity_ratio(audio_path: str) -> dict:
    """Simple energy-based voice activity estimate (not a VAD model)."""
    audio = load_audio_array(audio_path, sr=16000)
    sr = 16000
    if audio.size == 0:
        return {"speechRatio": 0.0, "speechDuration": 0.0, "totalDuration": 0.0}

    frame_len = int(0.05 * sr)  # 50ms
    hop = frame_len
    rms_vals = []
    for i in range(0, len(audio) - frame_len + 1, hop):
        frame = audio[i : i + frame_len]
        rms_vals.append(float(np.sqrt(np.mean(frame * frame))))
    rms_arr = np.array(rms_vals) if rms_vals else np.array([0.0])

    total_dur = audio_duration_sec_from_path(audio_path)
    mean_rms = float(np.mean(rms_arr))
    thr = max(0.01, mean_rms * 0.5)
    speech_ratio = float(np.mean(rms_arr >= thr))

    return {
        "speechRatio": round(speech_ratio, 3),
        "speechDuration": round(speech_ratio * total_dur, 2),
        "totalDuration": round(total_dur, 2),
        "threshold": round(thr, 4),
    }


def estimate_pitch_hz(frame: np.ndarray, sr: int) -> Optional[float]:
    """Very lightweight autocorrelation pitch estimate; returns None if unreliable."""
    if frame.size < int(0.03 * sr):
        return None
    frame = frame - np.mean(frame)
    energy = float(np.dot(frame, frame))
    if energy < 1e-6:
        return None

    corr = np.correlate(frame, frame, mode="full")[frame.size - 1 :]
    corr[0] = 0.0

    # Search plausible human pitch range: 80–300 Hz
    min_lag = int(sr / 300)
    max_lag = int(sr / 80)
    if max_lag <= min_lag + 2 or max_lag >= corr.size:
        return None

    window = corr[min_lag:max_lag]
    lag = int(np.argmax(window)) + min_lag
    peak = float(corr[lag])
    if peak <= 0.0:
        return None
    pitch = sr / lag
    return float(pitch)

