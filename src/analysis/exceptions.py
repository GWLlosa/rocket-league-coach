"""Custom exceptions for analysis and replay processing."""


class AnalysisException(Exception):
    """Base exception for analysis-related errors."""
    
    def __init__(self, message: str, replay_id: str = None, player_name: str = None):
        super().__init__(message)
        self.message = message
        self.replay_id = replay_id
        self.player_name = player_name


class ReplayParsingException(AnalysisException):
    """Exception raised when replay parsing fails."""
    
    def __init__(self, message: str, replay_id: str = None, file_path: str = None):
        super().__init__(message, replay_id=replay_id)
        self.file_path = file_path


class CorruptedReplayException(ReplayParsingException):
    """Exception raised when a replay file is corrupted or invalid."""
    
    def __init__(self, replay_id: str = None, file_path: str = None):
        message = f"Replay file is corrupted or invalid"
        if replay_id:
            message += f" (ID: {replay_id})"
        if file_path:
            message += f" (File: {file_path})"
        super().__init__(message, replay_id=replay_id, file_path=file_path)


class UnsupportedReplayVersionException(ReplayParsingException):
    """Exception raised when replay version is not supported."""
    
    def __init__(self, version: str = None, replay_id: str = None):
        message = f"Replay version not supported"
        if version:
            message += f": {version}"
        super().__init__(message, replay_id=replay_id)
        self.version = version


class PlayerNotFoundException(AnalysisException):
    """Exception raised when target player is not found in replay."""
    
    def __init__(self, player_name: str, replay_id: str = None):
        message = f"Player '{player_name}' not found in replay"
        if replay_id:
            message += f" (ID: {replay_id})"
        super().__init__(message, replay_id=replay_id, player_name=player_name)


class MetricsExtractionException(AnalysisException):
    """Exception raised when metrics extraction fails."""
    
    def __init__(self, message: str, metric_name: str = None, replay_id: str = None):
        super().__init__(message, replay_id=replay_id)
        self.metric_name = metric_name


class InsufficientDataException(AnalysisException):
    """Exception raised when there's insufficient data for analysis."""
    
    def __init__(self, message: str, required_count: int = None, actual_count: int = None):
        super().__init__(message)
        self.required_count = required_count
        self.actual_count = actual_count


class StatisticalAnalysisException(AnalysisException):
    """Exception raised during statistical analysis."""
    
    def __init__(self, message: str, analysis_type: str = None):
        super().__init__(message)
        self.analysis_type = analysis_type


class InvalidMetricException(AnalysisException):
    """Exception raised when an invalid metric is requested."""
    
    def __init__(self, metric_name: str, available_metrics: list = None):
        message = f"Invalid metric: {metric_name}"
        if available_metrics:
            message += f". Available metrics: {', '.join(available_metrics)}"
        super().__init__(message)
        self.metric_name = metric_name
        self.available_metrics = available_metrics


class AnalysisTimeoutException(AnalysisException):
    """Exception raised when analysis takes too long."""
    
    def __init__(self, timeout_seconds: int, operation: str = None):
        message = f"Analysis timed out after {timeout_seconds} seconds"
        if operation:
            message += f" during {operation}"
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class CarballException(AnalysisException):
    """Exception raised when carball library encounters an error."""
    
    def __init__(self, message: str, original_exception: Exception = None, replay_id: str = None):
        super().__init__(message, replay_id=replay_id)
        self.original_exception = original_exception


class MemoryException(AnalysisException):
    """Exception raised when memory usage exceeds limits."""
    
    def __init__(self, message: str, memory_usage_mb: float = None):
        super().__init__(message)
        self.memory_usage_mb = memory_usage_mb
