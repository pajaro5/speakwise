class SpeakWiseError(Exception):
    """Base class for all domain errors in SpeakWise."""


class ProviderUnavailableError(SpeakWiseError):
    """An external provider (STT/TTS/LLM) failed or is unreachable."""


class InvalidAudioError(SpeakWiseError):
    """Audio input could not be processed."""


class UnknownProviderError(SpeakWiseError):
    """A provider name from config doesn't match any implementation."""
