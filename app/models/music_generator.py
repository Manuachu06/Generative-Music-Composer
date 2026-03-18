from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import math
import struct
import uuid
import wave


@dataclass
class GenerationResult:
    track_id: str
    title: str
    local_path: str
    waveform_peaks: list[float]


class MusicGenerator:
    """Deterministic synth-based generator for end-to-end product prototyping.

    A production deployment can replace this with MusicGen, AudioCraft, or another
    model while preserving the same interface and response shape.
    """

    def generate(self, prompt_tags: list[str], duration_sec: int) -> GenerationResult:
        track_id = f"track_{uuid.uuid4().hex[:10]}"
        title = self._title_from_tags(prompt_tags)

        output_dir = Path("tmp")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{track_id}.wav"

        sample_rate = 16000
        n_samples = duration_sec * sample_rate
        root_freq = 180 + (sum(len(tag) for tag in prompt_tags) % 7) * 22
        overtone_freq = root_freq * 1.5
        accent_freq = root_freq * 2.0
        peaks: list[float] = []

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            window = max(1, n_samples // 48)
            acc = 0.0
            count = 0

            for index in range(n_samples):
                t = index / sample_rate
                swell = min(1.0, index / max(1, sample_rate * 0.8))
                pulse = 0.65 + 0.35 * math.sin(2 * math.pi * 0.18 * t)
                sample = swell * pulse * (
                    0.46 * math.sin(2 * math.pi * root_freq * t)
                    + 0.28 * math.sin(2 * math.pi * overtone_freq * t)
                    + 0.14 * math.sin(2 * math.pi * accent_freq * t)
                )
                pcm = int(max(-1.0, min(1.0, sample)) * 32767)
                wav_file.writeframesraw(struct.pack("<h", pcm))
                acc += abs(sample)
                count += 1
                if count >= window:
                    peaks.append(round(min(1.0, acc / count), 3))
                    acc = 0.0
                    count = 0

        return GenerationResult(
            track_id=track_id,
            title=title,
            local_path=str(path),
            waveform_peaks=peaks[:48],
        )

    def encode_data_uri(self, local_path: str) -> str:
        raw = Path(local_path).read_bytes()
        encoded = base64.b64encode(raw).decode("ascii")
        return f"data:audio/wav;base64,{encoded}"

    def _title_from_tags(self, prompt_tags: list[str]) -> str:
        lead = prompt_tags[0].replace("-", " ").title() if prompt_tags else "Adaptive"
        support = prompt_tags[1].replace("-", " ").title() if len(prompt_tags) > 1 else "Soundscape"
        return f"{lead} {support} Session"
