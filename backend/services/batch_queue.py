"""Batch queue for Anthropic API — accumulates requests and submits in bulk.

When the queue reaches a threshold (50 requests or 5-minute window),
it submits a batch to the Anthropic Message Batches API and polls for results.
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger(__name__)

BATCH_SIZE_THRESHOLD = 50
BATCH_TIME_WINDOW_S = 300  # 5 minutes


@dataclass
class BatchRequest:
    """A single request waiting in the batch queue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: list = field(default_factory=list)
    model: str = ""
    max_tokens: int = 4096
    system: str = ""
    callback: Optional[Callable] = None
    queued_at: float = field(default_factory=time.monotonic)


@dataclass
class BatchResult:
    """Result of a batch request."""
    request_id: str = ""
    content: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None


class BatchQueue:
    """Accumulates Anthropic API requests and submits them in batches."""

    def __init__(self, api_key: Optional[str] = None):
        self._queue: list[BatchRequest] = []
        self._lock = threading.Lock()
        self._api_key = api_key
        self._batch_timer: Optional[threading.Timer] = None
        self._pending_batches: dict[str, list[BatchRequest]] = {}
        self._results: dict[str, BatchResult] = {}

    def enqueue(self, request: BatchRequest) -> str:
        """Add a request to the batch queue. Returns request ID."""
        with self._lock:
            self._queue.append(request)
            logger.debug("Batch queue: %d requests pending", len(self._queue))

            if len(self._queue) >= BATCH_SIZE_THRESHOLD:
                self._submit_batch()
            elif self._batch_timer is None:
                self._batch_timer = threading.Timer(BATCH_TIME_WINDOW_S, self._submit_batch)
                self._batch_timer.daemon = True
                self._batch_timer.start()

        return request.id

    def _submit_batch(self) -> None:
        """Submit accumulated requests as a batch to the Anthropic API."""
        with self._lock:
            if not self._queue:
                return
            batch = list(self._queue)
            self._queue.clear()
            if self._batch_timer:
                self._batch_timer.cancel()
                self._batch_timer = None

        batch_id = str(uuid.uuid4())
        self._pending_batches[batch_id] = batch
        logger.info("Submitting batch %s with %d requests", batch_id, len(batch))

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key)

            # Build batch requests in the Anthropic batch format
            requests = []
            for req in batch:
                conv_messages = []
                for msg in req.messages:
                    if hasattr(msg, "role") and hasattr(msg, "content"):
                        if msg.role != "system":
                            conv_messages.append({"role": msg.role, "content": msg.content})
                    elif isinstance(msg, dict):
                        if msg.get("role") != "system":
                            conv_messages.append(msg)

                requests.append({
                    "custom_id": req.id,
                    "params": {
                        "model": req.model,
                        "max_tokens": req.max_tokens,
                        "messages": conv_messages,
                        **({"system": req.system} if req.system else {}),
                    },
                })

            # Submit batch
            batch_response = client.messages.batches.create(requests=requests)
            logger.info("Batch %s submitted, API batch_id: %s", batch_id, batch_response.id)

            # Poll for results
            threading.Thread(
                target=self._poll_batch,
                args=(client, batch_response.id, batch_id, batch),
                daemon=True,
            ).start()

        except Exception as e:
            logger.error("Batch submission failed: %s", e)
            for req in batch:
                self._results[req.id] = BatchResult(
                    request_id=req.id,
                    error=f"Batch submission failed: {e}",
                )
                if req.callback:
                    req.callback(self._results[req.id])

    def _poll_batch(self, client, api_batch_id: str, batch_id: str, batch: list[BatchRequest]) -> None:
        """Poll for batch completion and distribute results."""
        max_polls = 120  # 10 minutes at 5s intervals
        for _ in range(max_polls):
            time.sleep(5)
            try:
                status = client.messages.batches.retrieve(api_batch_id)
                if status.processing_status == "ended":
                    # Fetch results
                    results = list(client.messages.batches.results(api_batch_id))
                    result_map = {r.custom_id: r for r in results}

                    for req in batch:
                        r = result_map.get(req.id)
                        if r and r.result.type == "succeeded":
                            msg = r.result.message
                            content = "".join(
                                b.text for b in msg.content if b.type == "text"
                            )
                            br = BatchResult(
                                request_id=req.id,
                                content=content,
                                input_tokens=msg.usage.input_tokens,
                                output_tokens=msg.usage.output_tokens,
                            )
                        else:
                            br = BatchResult(
                                request_id=req.id,
                                error=f"Batch item failed: {r.result.type if r else 'missing'}",
                            )
                        self._results[req.id] = br
                        if req.callback:
                            req.callback(br)

                    logger.info("Batch %s completed, %d results", batch_id, len(results))
                    del self._pending_batches[batch_id]
                    return
            except Exception as e:
                logger.warning("Batch poll error: %s", e)

        logger.error("Batch %s timed out after polling", batch_id)

    def get_result(self, request_id: str) -> Optional[BatchResult]:
        """Get result for a specific request, or None if not ready."""
        return self._results.get(request_id)

    def get_stats(self) -> dict:
        return {
            "queue_size": len(self._queue),
            "pending_batches": len(self._pending_batches),
            "completed_results": len(self._results),
        }


# Singleton
_batch_queue: Optional[BatchQueue] = None


def get_batch_queue(api_key: Optional[str] = None) -> BatchQueue:
    global _batch_queue
    if _batch_queue is None:
        import os
        _batch_queue = BatchQueue(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
    return _batch_queue
