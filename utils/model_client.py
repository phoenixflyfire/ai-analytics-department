import asyncio
import math
import random
import re
import time
from google.adk.models import LiteLlm


def create_lite_llm(
    model: str,
    provider: str = "google",
    timeout: float = 1200.0,
    max_retries: int = 10,
    base_delay: float = 4.0,
) -> LiteLlm:
    return _RetryLiteLlm(
        model=model,
        provider=provider,
        timeout=timeout,
        num_retries=max_retries,
        retry_delay=base_delay,
    )


SUPPRESS_THOUGHTS = True


def _jitter(value: float, factor: float = 0.25) -> float:
    return value * random.uniform(1 - factor, 1 + factor)

def _filter_thoughts(item):
    if not SUPPRESS_THOUGHTS:
        return True
    if item.content and item.content.parts:
        filtered = [p for p in item.content.parts if not p.thought]
        if not filtered:
            return False
        item.content.parts = filtered
    return True


class _RetryLiteLlm(LiteLlm):
    async def generate_content_async(self, *args, **kwargs):
        import litellm

        last_error = None
        delay = self._additional_args.get("retry_delay", 4.0)
        max_retries = self._additional_args.get("num_retries", 5)

        for attempt in range(max_retries + 1):
            try:
                async for item in super().generate_content_async(*args, **kwargs):
                    if _filter_thoughts(item):
                        yield item
                return
            except litellm.InternalServerError as e:
                last_error = e
                if attempt < max_retries:
                    wait = _jitter(delay)
                    print(f"⚠️ API 500 error (attempt {attempt + 1}/{max_retries}), retrying in {wait:.0f}s...")
                    await asyncio.sleep(wait)
                    delay *= 1.5
                else:
                    print(f"❌ API 500 error after {max_retries} retries, giving up.")
            except litellm.RateLimitError as e:
                last_error = e
                retry_after = _extract_retry_delay(e, default=30.0)
                print(f"⏳ Rate limit hit (attempt {attempt + 1}/{max_retries}), retrying in {retry_after:.0f}s...")
                await asyncio.sleep(retry_after)
                if attempt >= max_retries:
                    print(f"❌ Rate limit error after {max_retries} retries, giving up.")
        raise last_error


def _extract_retry_delay(error: Exception, default: float = 30.0) -> float:
    """Parse retry delay from a RateLimitError's response or message."""
    import json
    text = str(error)
    # Try to extract "retryDelay": "29s" from nested JSON in the error text
    match = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', text)
    if match:
        return math.ceil(float(match.group(1)))
    # Fallback: extract "Please retry in Xs" from message
    match = re.search(r"retry in\s+([\d.]+)s", text)
    if match:
        return math.ceil(float(match.group(1)))
    return default
