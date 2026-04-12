# -*- coding: utf-8 -*-
"""
Audio Utilities Module
Extracts basic audio features: RMS energy, pitch (F0), duration, and statistics.
Used for pronunciation fallback and confidence scoring.
"""
import numpy as np
import subprocess
import os
import shutil
from typing import Optional, Tuple


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


def load_audio(audio_path: str, sr: int = 16000) -> Tuple[np.ndarray, int]:
    """
    1️⃣ Load audio
    
    Takes an audio file path, loads it as a waveform array.
    Resamples to 16 kHz and converts to mono.
    
    Args:
        audio_path: Path to audio file
        sr: Target sample rate (default: 16000)
    
    Returns:
        Tuple of (audio_array, sample_rate)
        audio_array: float32 mono waveform
        sample_rate: Should be 16000
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
        "1",  # Mono
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sr),  # Resample to target sample rate
        "-",
    ]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    audio = np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
    return audio, sr


def get_duration(audio_array: np.ndarray, sample_rate: int) -> float:
    """
    2️⃣ Get duration
    
    From the audio array and sample rate, compute duration.
    
    Args:
        audio_array: Audio waveform array
        sample_rate: Sample rate in Hz
    
    Returns:
        Duration in seconds
    """
    if audio_array.size == 0:
        return 0.0
    return float(audio_array.size) / float(sample_rate)


def compute_rms_frames(audio_array: np.ndarray, sample_rate: int, frame_size_ms: float = 25.0) -> np.ndarray:
    """
    3️⃣ Compute RMS energy per frame
    
    Split audio into small frames (default: 25 ms).
    For each frame, compute RMS (root mean square energy).
    
    Args:
        audio_array: Audio waveform array
        sample_rate: Sample rate in Hz
        frame_size_ms: Frame size in milliseconds (default: 25.0)
    
    Returns:
        Array of RMS values per frame
    """
    if audio_array.size == 0:
        return np.array([0.0])
    
    frame_len = int((frame_size_ms / 1000.0) * sample_rate)  # Convert ms to samples
    hop = frame_len  # No overlap for now
    
    rms_vals = []
    for i in range(0, len(audio_array) - frame_len + 1, hop):
        frame = audio_array[i : i + frame_len]
        rms = float(np.sqrt(np.mean(frame * frame)))
        rms_vals.append(rms)
    
    return np.array(rms_vals) if rms_vals else np.array([0.0])


def estimate_pitch_hz(frame: np.ndarray, sr: int) -> Optional[float]:
    """
    Very lightweight autocorrelation pitch estimate; returns None if unreliable.
    
    Args:
        frame: Audio frame (numpy array)
        sr: Sample rate in Hz
    
    Returns:
        Pitch in Hz, or None if unreliable
    """
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


def compute_pitch_frames(audio_array: np.ndarray, sample_rate: int, frame_size_ms: float = 25.0) -> np.ndarray:
    """
    4️⃣ Compute pitch (F0) over time
    
    Extract pitch values for frames across audio.
    Ignore unvoiced frames (zeros / NaN).
    
    Args:
        audio_array: Audio waveform array
        sample_rate: Sample rate in Hz
        frame_size_ms: Frame size in milliseconds (default: 25.0)
    
    Returns:
        Array of pitch values (Hz), with None/NaN for unvoiced frames filtered out
    """
    if audio_array.size == 0:
        return np.array([])
    
    frame_len = int((frame_size_ms / 1000.0) * sample_rate)
    hop = frame_len
    
    pitch_vals = []
    for i in range(0, len(audio_array) - frame_len + 1, hop):
        frame = audio_array[i : i + frame_len]
        pitch = estimate_pitch_hz(frame, sample_rate)
        if pitch is not None:
            pitch_vals.append(pitch)
    
    return np.array(pitch_vals) if pitch_vals else np.array([])


def compute_rms_stats(rms_frames: np.ndarray) -> dict:
    """
    5️⃣ Helper: Compute RMS statistics
    
    Computes mean RMS, std RMS, and coefficient of variation.
    
    Args:
        rms_frames: Array of RMS values per frame
    
    Returns:
        Dictionary with:
        - mean_rms: Mean RMS value
        - std_rms: Standard deviation of RMS
        - cv_rms: Coefficient of variation (std / mean)
    """
    if rms_frames.size == 0:
        return {
            "mean_rms": 0.0,
            "std_rms": 0.0,
            "cv_rms": 0.0,
        }
    
    mean_rms = float(np.mean(rms_frames))
    std_rms = float(np.std(rms_frames))
    cv_rms = std_rms / (mean_rms + 1e-6)  # Coefficient of variation
    
    return {
        "mean_rms": float(mean_rms),
        "std_rms": float(std_rms),
        "cv_rms": float(cv_rms),
    }


def compute_pitch_stats(pitch_frames: np.ndarray) -> dict:
    """
    5️⃣ Helper: Compute pitch statistics
    
    Computes mean pitch, std pitch, and coefficient of variation.
    
    Args:
        pitch_frames: Array of pitch values (Hz)
    
    Returns:
        Dictionary with:
        - mean_pitch: Mean pitch in Hz
        - std_pitch: Standard deviation of pitch
        - cv_pitch: Coefficient of variation (std / mean)
    """
    if pitch_frames.size == 0:
        return {
            "mean_pitch": 0.0,
            "std_pitch": 0.0,
            "cv_pitch": 0.0,
        }
    
    mean_pitch = float(np.mean(pitch_frames))
    std_pitch = float(np.std(pitch_frames))
    cv_pitch = std_pitch / (mean_pitch + 1e-6)  # Coefficient of variation
    
    return {
        "mean_pitch": float(mean_pitch),
        "std_pitch": float(std_pitch),
        "cv_pitch": float(cv_pitch),
    }

