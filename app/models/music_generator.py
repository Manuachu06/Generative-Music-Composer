from dataclasses import dataclass
from pathlib import Path
import uuid


@dataclass
class GenerationResult:
    track_id: str
    local_path: str


class MusicGenerator:
    """Wrapper abstraction for AudioCraft/MusicGen inference."""

    def generate(self, prompt_tags: list[str], duration_sec: int) -> GenerationResult:
        track_id = f"track_{uuid.uuid4().hex[:10]}"
        output_dir = Path("tmp")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{track_id}.wav"
        path.write_bytes(f"placeholder audio for {prompt_tags} ({duration_sec}s)".encode("utf-8"))
        return GenerationResult(track_id=track_id, local_path=str(path))
