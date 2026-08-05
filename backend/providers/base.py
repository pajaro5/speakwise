from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Transcript:
    text: str
    wpm: float
    words: list[dict] = field(default_factory=list)
    phonemes: list[dict] = field(default_factory=list)
    fillers: int = 0
    stress_results: list[dict] = field(default_factory=list)


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes) -> Transcript: ...


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice: str = "default") -> bytes: ...


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self, messages: list[dict], system: str, max_tokens: int = 400
    ) -> str: ...
