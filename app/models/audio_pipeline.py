from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import math
from statistics import mean


@dataclass
class AudioFeatures:
    transcript: str
    emotion: str
    performance_type: str
    energy: float
    pitch_signature: str
    embedding: list[float]


class AudioPipeline:
    """Interprets optional voice commands or sung reference snippets.

    This MVP intentionally avoids permanent storage: audio is analyzed in-memory,
    converted into simple descriptors, and discarded once generation is finished.
    """

    def extract(
        self,
        voice_command_text: str | None = None,
        voice_reference_base64: str | None = None,
        transcript_hint: str | None = None,
    ) -> AudioFeatures:
        transcript = (voice_command_text or transcript_hint or "").strip()
        raw_audio = self._decode_audio(voice_reference_base64)

        if not raw_audio and not transcript:
            return AudioFeatures(
                transcript="",
                emotion="neutral",
                performance_type="none",
                energy=0.2,
                pitch_signature="mid",
                embedding=[0.0] * 8,
            )

        energy = self._estimate_energy(raw_audio) if raw_audio else 0.35
        emotion = self._emotion_from_inputs(transcript, energy)
        performance_type = "sung-reference" if raw_audio else "voice-command"
        pitch_signature = self._pitch_signature(raw_audio)
        embedding = self._hash_embedding(transcript, raw_audio)

        return AudioFeatures(
            transcript=transcript,
            emotion=emotion,
            performance_type=performance_type,
            energy=energy,
            pitch_signature=pitch_signature,
            embedding=embedding,
        )

    def _decode_audio(self, value: str | None) -> bytes:
        if not value:
            return b""
        if "," in value:
            value = value.split(",", 1)[1]
        try:
            return base64.b64decode(value)
        except Exception:
            return b""

    def _estimate_energy(self, raw_audio: bytes) -> float:
        if not raw_audio:
            return 0.2
        sample = raw_audio[:4000]
        centered = [abs(byte - 128) / 128 for byte in sample]
        return max(0.1, min(1.0, mean(centered)))

    def _emotion_from_inputs(self, transcript: str, energy: float) -> str:
        text = transcript.lower()
        if any(token in text for token in ["calm", "peaceful", "sleep", "soft"]):
            return "calm"
        if any(token in text for token in ["epic", "strong", "powerful"]):
            return "dramatic"
        if any(token in text for token in ["happy", "bright", "uplifting"]):
            return "uplifting"
        if energy > 0.62:
            return "intense"
        if energy < 0.28:
            return "gentle"
        return "focused"

    def _pitch_signature(self, raw_audio: bytes) -> str:
        if not raw_audio:
            return "mid"
        avg = sum(raw_audio[:1200]) / max(1, len(raw_audio[:1200]))
        if avg < 90:
            return "low"
        if avg > 165:
            return "high"
        return "mid"

    def _hash_embedding(self, transcript: str, raw_audio: bytes, size: int = 8) -> list[float]:
        seed = transcript.encode("utf-8") + raw_audio[:2048]
        values: list[float] = []
        for index in range(size):
            digest = hashlib.sha256(index.to_bytes(2, "little") + seed).digest()
            raw = int.from_bytes(digest[:4], "little", signed=False)
            values.append((raw / 2**32) * 2 - 1)
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]
