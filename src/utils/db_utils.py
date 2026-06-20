import asyncio
from typing import Awaitable, TypeVar, Tuple

T = TypeVar("T")


async def run_with_timeout(coro: Awaitable[T], timeout: int = 30) -> Tuple[bool, T | Exception]:
    """
    Runs an awaitable with a timeout.
    Returns (success: bool, result_or_exception)
    """

    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return True, result
    except asyncio.TimeoutError as e:
        return False, e
    except Exception as e:
        return False, e