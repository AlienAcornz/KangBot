import asyncio
from typing import Any, Tuple, Awaitable


async def run_with_timeout(func: Awaitable, timeout: int = 30) -> Tuple[bool, Any]:
    """
    Runs an awaitable with a timeout.
    Returns (success: bool, result_or_exception)
    """

    try:
        result = await asyncio.wait_for(func, timeout=timeout)
        return True, result
    except asyncio.TimeoutError as e:
        return False, e
    except Exception as e:
        return False, e