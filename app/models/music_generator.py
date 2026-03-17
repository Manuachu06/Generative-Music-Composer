from dataclasses import dataclass
from pathlib import Path
import math
import struct
import uuid
import wave


@dataclass
class GenerationResult:
    track_id: str
    local_path: str


class MusicGenerator:
    """Wrapper abstraction for AudioCraft/MusicGen inference.

    Current implementation generates a valid WAV preview tone so users can listen end-to-end.
    Replace with AudioCraft/MusicGen model inference for real generation.
    """

    def generate(self, prompt_tags: list[str], duration_sec: int) -> GenerationResult:
        track_id = f"track_{uuid.uuid4().hex[:10]}"
        output_dir = Path("tmp")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{track_id}.wav"

        sample_rate = 32000
        n_samples = duration_sec * sample_rate
        base_freq = 220 + (len("".join(prompt_tags)) % 5) * 55

        with wave.open(str(path), "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for i in range(n_samples):
                t = i / sample_rate
                env = min(1.0, i / (sample_rate * 0.3))
                sample = 0.25 * env * (
                    math.sin(2 * math.pi * base_freq * t)
                    + 0.3 * math.sin(2 * math.pi * (base_freq * 1.5) * t)
                )
                pcm = int(max(-1.0, min(1.0, sample)) * 32767)
                wav_file.writeframesraw(struct.pack("<h", pcm))

        return GenerationResult(track_id=track_id, local_path=str(path))
