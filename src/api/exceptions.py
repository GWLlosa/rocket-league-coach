"""Custom exceptions for API integrations."""


class APIException(Exception):
    """Base exception for API-related errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data


class BallchasingAPIException(APIException):
    """Exception for Ballchasing API errors."""
    pass


class RateLimitExceededException(BallchasingAPIException):
    """Exception raised when API rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class UnauthorizedException(BallchasingAPIException):
    """Exception raised when API key is invalid or missing."""
    
    def __init__(self, message: str = "Unauthorized - check your API key"):
        super().__init__(message, status_code=401)


class ReplayNotFoundException(BallchasingAPIException):
    """Exception raised when a requested replay is not found."""
    
    def __init__(self, replay_id: str):
        super().__init__(f"Replay not found: {replay_id}", status_code=404)
        self.replay_id = replay_id


class PlayerNotFoundException(BallchasingAPIException):
    """Exception raised when no replays are found for a player."""
    
    def __init__(self, player_name: str):
        super().__init__(f"No replays found for player: {player_name}", status_code=404)
        self.player_name = player_name


class InvalidResponseException(BallchasingAPIException):
    """Exception raised when API response is invalid or malformed."""
    
    def __init__(self, message: str = "Invalid API response format"):
        super().__init__(message, status_code=None)


class NetworkException(BallchasingAPIException):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: str, original_exception: Exception = None):
        super().__init__(f"Network error: {message}")
        self.original_exception = original_exception


class DownloadException(BallchasingAPIException):
    """Exception raised when replay download fails."""
    
    def __init__(self, replay_id: str, message: str = None):
        error_msg = f"Failed to download replay {replay_id}"
        if message:
            error_msg += f": {message}"
        super().__init__(error_msg)
        self.replay_id = replay_id
