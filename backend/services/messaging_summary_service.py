"""LLM-based summary generation for messaging threads."""

import json
import logging
from typing import Optional

from backend.services.llm_client import ClaudeCLIClient, ChatGPTCLIClient, LLMMessage
from backend.models.agent_definition import ModelTier

logger = logging.getLogger(__name__)


def generate_thread_summary(
    subject: str,
    messages: list[dict],  # [{sender_name, body, created_at}, ...]
    max_retries: int = 2,
) -> tuple[str, Optional[str], list[str]]:
    """Generate a 2-3 sentence summary and extract core decision.

    Returns: (summary, decision, tags)
    """
    # Try to get an LLM client
    client = None
    try:
        client = ClaudeCLIClient()
    except Exception:
        try:
            client = ChatGPTCLIClient()
        except Exception:
            logger.warning(
                "No LLM client available; using fallback summary generation"
            )
            return _fallback_summary(subject, messages)

    if not client:
        return _fallback_summary(subject, messages)

    # Build conversation history
    message_text = "\n".join(
        [f"**{m['sender_name']}**: {m['body']}" for m in messages]
    )

    prompt = f"""You are summarizing a discussion thread from a drum corps collaboration system.

Thread Subject: {subject}

Messages:
{message_text}

Please provide:
1. A 2-3 sentence summary of the key discussion and outcome
2. The core decision (if any) in one sentence, or null if no decision
3. A list of 3-5 relevant tags (keywords)

Format your response as JSON:
{{
    "summary": "...",
    "decision": "..." or null,
    "tags": ["tag1", "tag2", "tag3"]
}}
"""

    for attempt in range(max_retries):
        try:
            resp = client.chat(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You are a professional summarizer for drum corps collaboration. "
                            "Respond only with valid JSON."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                model_tier=ModelTier.HAIKU,
            )

            # Parse JSON response
            result = json.loads(resp.content)
            summary = result.get("summary", "")
            decision = result.get("decision")
            tags = result.get("tags", [])

            if summary and isinstance(tags, list):
                return summary, decision, tags
        except Exception as e:
            logger.warning(
                f"LLM summary generation attempt {attempt + 1} failed: {e}"
            )
            if attempt == max_retries - 1:
                logger.warning(
                    "Max retries reached; falling back to deterministic summary"
                )
                return _fallback_summary(subject, messages)

    return _fallback_summary(subject, messages)


def _fallback_summary(
    subject: str, messages: list[dict]
) -> tuple[str, Optional[str], list[str]]:
    """Generate a deterministic summary without LLM."""
    # Extract key words from subject and messages
    subject_words = subject.lower().split()
    message_bodies = [m.get("body", "") for m in messages]

    # Simple keyword extraction
    keywords = set()
    for word in subject_words:
        if len(word) > 3:
            keywords.add(word.strip(".,!?"))

    # Look for decision keywords
    decision = None
    all_text = " ".join([subject] + message_bodies).lower()
    if any(
        word in all_text
        for word in ["decision", "approved", "confirmed", "finalized", "resolved"]
    ):
        decision = "Decision recorded in thread messages"

    # Create simple summary from message count
    summary = f"Thread '{subject}' with {len(messages)} message(s). "
    if len(message_bodies) > 0:
        first_msg = message_bodies[0][:100]
        summary += f"Initial message: {first_msg}... "
    if decision:
        summary += "Decision was reached."

    tags = list(keywords)[: 5]  # Limit to 5 tags

    return summary, decision, tags
