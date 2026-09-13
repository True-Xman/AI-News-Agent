"""Expected failure types shared by the AI Signal Scout pipeline."""


class PipelineError(RuntimeError):
    """Base error for an expected pipeline failure."""


class ConfigurationError(PipelineError):
    """Required runtime configuration is unavailable."""


class ExternalServiceError(PipelineError):
    """An external dependency did not complete successfully."""


class ResponseValidationError(PipelineError):
    """An external response violated the expected contract."""
