import asyncio
import json
import logging
from typing import Any

from openai import (APIConnectionError, APIStatusError,
                    APITimeoutError, OpenAI, RateLimitError)

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.inline_comment import InlineComment
from app.models.submission import Submission
from app.services.submission_workflow import finalize_submission_review_status
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an assistant for a university teacher reviewing student code submissions.
Analyze only the task statement and the submitted code.
Always respond in Russian.
All natural language fields in the JSON response must be in Russian.
Be factual, concise, and neutral.
Do not assign a grade.
Do not mention that you are an AI model.
Return only a valid JSON object with this structure:
{
  "llm_comment": "string",
  "inline_comments": [
    {
      "line_start": 1,
      "line_end": 1,
      "text": "string"
    }
  ]
}
Requirements:
- "llm_comment" must be a coherent, connected summary for the teacher, ready for direct display without editing.
- "llm_comment" must not be formatted as sections, headings, or bullet lists.
- In one compact text, mention the main strengths of the solution, the important problems if they exist, and meaningful remarks about efficiency or code quality.
- Do not invent weaknesses if the solution is correct and clean.
- Focus on correctness relative to the task, code quality/style, likely bugs, and efficiency remarks only when they are meaningful.
- "inline_comments" should contain only useful factual comments tied to concrete code lines.
- Every text field must be written in Russian.
- Use 1-based line numbers.
- If a comment applies to a single line, set "line_end" equal to "line_start".
- If there are no useful inline comments, return an empty array.
- Do not include markdown fences.
""".strip()


def log_debug(message: str, **kwargs: Any) -> None:
    if not settings.LLM_DEBUG_LOGGING:
        return

    if kwargs:
        logger.warning("LLM DEBUG: %s | %s", message, kwargs)
    else:
        logger.warning("LLM DEBUG: %s", message)


def extract_json_payload(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def build_user_prompt(task_text: str, code: str, language: str) -> str:
    numbered_code = "\n".join(
        f"{index + 1}: {line}" for index, line in enumerate(code.splitlines())
    )
    if not numbered_code:
        numbered_code = "1: "

    return (
        "Task statement:\n"
        f"{task_text}\n\n"
        "Submission language:\n"
        f"{language}\n\n"
        "Code with line numbers:\n"
        f"{numbered_code}"
    )


def build_model_uri(model_name: str) -> str:
    if not settings.YANDEX_FOLDER_ID:
        raise RuntimeError("YANDEX_FOLDER_ID is not configured")
    return f"gpt://{settings.YANDEX_FOLDER_ID}/{model_name}"


def build_client() -> OpenAI:
    if not settings.YANDEX_API_KEY:
        raise RuntimeError("YANDEX_API_KEY is not configured")
    if not settings.YANDEX_FOLDER_ID:
        raise RuntimeError("YANDEX_FOLDER_ID is not configured")

    return OpenAI(
        api_key=settings.YANDEX_API_KEY,
        base_url=settings.YANDEX_BASE_URL,
        project=settings.YANDEX_FOLDER_ID,
        timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
    )


def request_model_completion(
        task_text: str, code: str, language: str
) -> dict[str, Any]:
    client = build_client()
    prompt = build_user_prompt(task_text, code, language)
    last_error: Exception | None = None

    log_debug(
        "starting model completion",
        language=language,
        task_length=len(task_text),
        code_length=len(code),
        prompt_length=len(prompt),
    )

    for model_name in (settings.YANDEX_MAIN_MODEL, settings.YANDEX_FALLBACK_MODEL):
        try:
            model_uri = build_model_uri(model_name)
            log_debug("sending request to model", model=model_uri)
            response = client.responses.create(
                model=model_uri,
                temperature=settings.LLM_TEMPERATURE,
                instructions=SYSTEM_PROMPT,
                input=prompt,
                max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            )
            content = (response.output_text or "").strip()
            log_debug(
                "received model response",
                model=model_uri,
                response_length=len(content),
                response_preview=content[:500],
            )
            if not content:
                raise ValueError(f"Empty response from model {model_name}")
            json_content = extract_json_payload(content)
            log_debug(
                "normalized model response for json parsing",
                model=model_uri,
                normalized_preview=json_content[:500],
            )
            payload = json.loads(json_content)
            log_debug(
                "parsed model json",
                model=model_uri,
                keys=list(payload.keys()) if isinstance(payload, dict) else None,
            )
            return payload
        except (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            RateLimitError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc
            log_debug(
                "model request failed",
                model=model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

    if last_error is None:
        raise RuntimeError("No models were configured for LLM analysis")
    raise last_error


def contains_cyrillic(text: str) -> bool:
    return any(
        0x0400 <= ord(char) <= 0x04FF
        or 0x0500 <= ord(char) <= 0x052F
        for char in text
    )


def normalize_comment_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("llm_comment must be a string")

    text = value.strip()
    if not text:
        raise ValueError("llm_comment must not be empty")
    if not contains_cyrillic(text):
        raise ValueError("llm_comment must be in Russian")

    return text


def normalize_inline_comments(items: Any, line_count: int) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        line_start = item.get("line_start")
        line_end = item.get("line_end")
        text = item.get("text")

        if line_end is None:
            line_end = line_start

        if not isinstance(line_start, int) or not isinstance(line_end, int):
            continue
        if not isinstance(text, str):
            continue

        comment_text = text.strip()
        if not comment_text:
            continue
        if not contains_cyrillic(comment_text):
            continue

        if line_start < 1 or line_end < line_start:
            continue
        if line_start > line_count:
            continue

        normalized.append(
            {
                "line_start": line_start,
                "line_end": min(line_end, line_count),
                "text": comment_text,
            }
        )

    return normalized


async def save_llm_result(
    submission_id: int,
    llm_comment: str | None,
    inline_comments: list[dict[str, Any]],
    *,
    completed: bool,
) -> None:
    log_debug(
        "saving llm result",
        submission_id=submission_id,
        completed=completed,
        has_comment=llm_comment is not None,
        inline_comments_count=len(inline_comments),
    )
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Submission)
            .options(selectinload(Submission.inline_comments))
            .where(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()
        if submission is None:
            log_debug(
                "submission disappeared before llm save", submission_id=submission_id
            )
            return

        submission.llm_comment = llm_comment
        submission.llm_completed = completed
        submission.inline_comments.clear()
        for comment in inline_comments:
            submission.inline_comments.append(
                InlineComment(
                    line_start=comment["line_start"],
                    line_end=comment["line_end"],
                    text=comment["text"],
                )
            )

        await db.commit()

    log_debug("llm result saved", submission_id=submission_id)
    await finalize_submission_review_status(submission_id)
    log_debug("submission review status finalized", submission_id=submission_id)


async def analyze_submission(submission_id: int, attempt: int = 0) -> None:
    log_debug(
        "analyze submission started", submission_id=submission_id, attempt=attempt
    )
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Submission)
            .options(joinedload(Submission.task))
            .where(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()
        if submission is None:
            log_debug(
                "submission not found for llm analysis", submission_id=submission_id
            )
            return

        task_text = submission.task.text
        code = submission.code
        language = submission.language.value
        log_debug(
            "loaded submission for llm analysis",
            submission_id=submission_id,
            task_id=submission.task_id,
            language=language,
            code_lines=max(1, len(code.splitlines())),
        )

    try:
        payload = await asyncio.to_thread(
            request_model_completion,
            task_text,
            code,
            language,
        )
        line_count = max(1, len(code.splitlines()))
        llm_comment = normalize_comment_text(payload.get("llm_comment"))
        inline_comments = normalize_inline_comments(
            payload.get("inline_comments", []),
            line_count,
        )
        log_debug(
            "normalized llm payload",
            submission_id=submission_id,
            comment_length=len(llm_comment),
            inline_comments_count=len(inline_comments),
        )
        await save_llm_result(
            submission_id,
            llm_comment,
            inline_comments,
            completed=True,
        )
    except Exception as exc:
        log_debug(
            "llm analysis failed",
            submission_id=submission_id,
            attempt=attempt,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        if attempt < settings.LLM_MAX_RETRIES:
            log_debug(
                "scheduling llm retry",
                submission_id=submission_id,
                next_attempt=attempt + 1,
                delay_seconds=settings.LLM_RETRY_DELAY_SECONDS,
            )
            await asyncio.sleep(settings.LLM_RETRY_DELAY_SECONDS)
            await analyze_submission(submission_id, attempt + 1)
            return

        log_debug(
            "llm exhausted retries, saving null result",
            submission_id=submission_id,
        )
        await save_llm_result(
            submission_id,
            None,
            [],
            completed=True,
        )
