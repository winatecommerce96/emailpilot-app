"""
Retry utilities with exponential backoff.
Classifies retryable vs non-retryable errors.
"""

import asyncio
import random
from typing import TypeVar, Callable, Any, Type, Tuple, Optional
from functools import wraps
import logging

from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)


logger = logging.getLogger(__name__)

T = TypeVar('T')


# Retryable exceptions
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    # Add more as needed
)

# Non-retryable exceptions  
NON_RETRYABLE_EXCEPTIONS = (
    ValueError,
    TypeError,
    KeyError,
    # Add more as needed
)


def is_retryable_error(exception: Exception) -> bool:
    """Determine if an error should be retried."""
    
    # Check for explicitly non-retryable
    if isinstance(exception, NON_RETRYABLE_EXCEPTIONS):
        return False
    
    # Check for explicitly retryable
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True
    
    # HTTP status codes (if available)
    if hasattr(exception, 'status_code'):
        status = exception.status_code
        # Retry on 5xx and some 4xx
        if 500 <= status < 600:
            return True
        if status in [429, 408, 409]:  # Rate limit, timeout, conflict
            return True
        return False
    
    # Default to retryable for unknown exceptions
    return True


def exponential_backoff_with_jitter(
    min_delay: float = 1.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0,
    jitter: float = 0.1
) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds  
        multiplier: Backoff multiplier
        jitter: Random jitter factor (0.0 to 1.0)
    
    Returns:
        Delay in seconds
    """
    
    # Calculate base delay
    delay = min_delay
    
    # Add jitter
    jitter_amount = delay * jitter * random.random()
    delay += jitter_amount
    
    # Cap at maximum
    return min(delay, max_delay)


def with_retries(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        backoff_factor: Exponential backoff factor
        jitter: Whether to add random jitter
        retryable_exceptions: Custom exceptions to retry on
    """
    
    if retryable_exceptions is None:
        retryable_exceptions = RETRYABLE_EXCEPTIONS
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_delay,
                max=max_delay,
                jitter=jitter
            ),
            retry=retry_if_exception_type(retryable_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if not is_retryable_error(e):
                    # Don't retry non-retryable errors
                    raise
                # Let tenacity handle retryable errors
                raise
        
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_delay,
                max=max_delay,
                jitter=jitter
            ),
            retry=retry_if_exception_type(retryable_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not is_retryable_error(e):
                    # Don't retry non-retryable errors
                    raise
                # Let tenacity handle retryable errors
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RetryContext:
    """Context manager for retry operations with detailed logging."""
    
    def __init__(
        self,
        operation_name: str,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ):
        self.operation_name = operation_name
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.attempt = 0
        self.total_delay = 0.0
    
    async def __aenter__(self):
        self.attempt += 1
        logger.info(
            f"Starting {self.operation_name} attempt {self.attempt}/{self.max_attempts}"
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success
            logger.info(
                f"{self.operation_name} succeeded on attempt {self.attempt}"
            )
            return True
        
        if not is_retryable_error(exc_val):
            # Non-retryable error
            logger.error(
                f"{self.operation_name} failed with non-retryable error: {exc_val}"
            )
            return False
        
        if self.attempt >= self.max_attempts:
            # Max attempts reached
            logger.error(
                f"{self.operation_name} failed after {self.max_attempts} attempts: {exc_val}"
            )
            return False
        
        # Calculate delay for next attempt
        delay = self.initial_delay * (self.backoff_factor ** (self.attempt - 1))
        delay = min(delay, 60.0)  # Cap at 60 seconds
        
        # Add jitter
        jitter = delay * 0.1 * random.random()
        delay += jitter
        
        self.total_delay += delay
        
        logger.warning(
            f"{self.operation_name} attempt {self.attempt} failed: {exc_val}. "
            f"Retrying in {delay:.2f}s..."
        )
        
        await asyncio.sleep(delay)
        return True
    
    def should_retry(self, exception: Exception) -> bool:
        """Check if operation should be retried."""
        return (
            self.attempt < self.max_attempts and
            is_retryable_error(exception)
        )