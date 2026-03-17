from dataclasses import dataclass


@dataclass
class AudioFeatures:
    transcript: str
    emotion: str
    embedding: list[float]


class AudioPipeline:
    """Pluggable audio pipeline.

    Replace stub logic with faster-whisper + SER model inference in production.
    """

    def extract(self, audio_uri: str | None) -> AudioFeatures:
        if not audio_uri:
            return AudioFeatures(transcript="", emotion="neutral", embedding=[0.0] * 8)

        transcript = "transcript from whisper"
        emotion = "calm"
        embedding = [0.11, 0.03, 0.67, 0.42, 0.08, 0.22, 0.55, 0.09]
        return AudioFeatures(transcript=transcript, emotion=emotion, embedding=embedding)
