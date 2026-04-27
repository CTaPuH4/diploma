import os
import shutil
import subprocess
import tempfile

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.submission import Submission, SubmissionStatus
from app.models.test_case import TestCase
from app.services.submission_workflow import finalize_submission_review_status
from sqlalchemy import select

DOCKER_IMAGE = settings.JUDGE_IMAGE
TIMEOUT = settings.JUDGE_TIMEOUT_SECONDS


def build_run_command(container: str) -> list[str]:
    return [
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        container,
        "--network",
        "none",
        "--memory",
        settings.JUDGE_MEMORY_LIMIT,
        "--cpus",
        settings.JUDGE_CPU_LIMIT,
        "--pids-limit",
        str(settings.JUDGE_PIDS_LIMIT),
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        DOCKER_IMAGE,
        "sleep",
        "30",
    ]


def format_test_result(
    passed: int,
    total: int,
    *,
    summary: str | None = None,
    results: list[dict] | None = None,
) -> str:
    parts = [f"PASSED: {passed}/{total}"]

    if summary:
        parts.append(summary)

    if results:
        parts.append(
            "\n".join(
                f"Input: {r['input']}\n"
                f"Expected: {r['expected']}\n"
                f"Actual: {r['actual']}\n"
                f"Status: {r['status']}\n"
                "------"
                for r in results
            )
        )

    return "\n\n".join(parts)


def run(cmd, input_data=None):
    try:
        if isinstance(input_data, str):
            input_data = input_data.encode()

        p = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            timeout=TIMEOUT,
        )

        return (
            p.stdout.decode(errors="ignore"),
            p.stderr.decode(errors="ignore"),
            p.returncode,
        )
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1


def docker_exec(container, cmd, input_data=None):
    return run(["docker", "exec", "-i", container] + cmd, input_data)


def compile_cpp(container, filename):
    return docker_exec(container, ["g++", filename, "-O2", "-o", "main.out"])


def run_cpp(container, input_data):
    return docker_exec(container, ["./main.out"], input_data)


def run_python(container, filename, input_data):
    return docker_exec(container, ["python", filename], input_data)


def normalize(s: str) -> str:
    return (s or "").strip().replace("\r", "")


async def judge_submission(submission_id: int, code: str, task_id: int, language: str):
    print(f"JUDGE START: {submission_id}")

    async with AsyncSessionLocal() as db:
        submission = await db.get(Submission, submission_id)
        if submission is None:
            return

        submission.status = SubmissionStatus.analyzing
        await db.commit()

        result = await db.execute(select(TestCase).where(TestCase.task_id == task_id))
        tests = result.scalars().all()

        if not tests:
            submission.test_result = format_test_result(
                0,
                0,
                summary="No test cases configured for this task",
            )
            await db.commit()
            await finalize_submission_review_status(submission_id)
            return

        temp_dir = tempfile.mkdtemp()
        container = f"judge_{submission_id}"

        try:
            _, err, rc = run(build_run_command(container))
            if rc != 0:
                submission.test_result = format_test_result(
                    0,
                    len(tests),
                    summary=f"JUDGE START ERROR:\n{err}",
                )
                await db.commit()
                await finalize_submission_review_status(submission_id)
                return

            filename = "main.py" if language == "python" else "main.cpp"
            filepath = os.path.join(temp_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            run(["docker", "cp", filepath, f"{container}:/app/{filename}"])

            if language == "cpp":
                out, err, rc = compile_cpp(container, filename)
                if rc != 0:
                    submission.test_result = format_test_result(
                        0,
                        len(tests),
                        summary=f"COMPILATION ERROR:\n{err}",
                    )
                    await db.commit()
                    await finalize_submission_review_status(submission_id)
                    return

            results = []
            passed = 0

            for t in tests:
                expected = normalize(t.output)

                if language == "python":
                    stdout, stderr, rc = run_python(container, filename, t.input)
                else:
                    stdout, stderr, rc = run_cpp(container, t.input)

                if rc == -1 and stderr == "TIMEOUT":
                    results.append(
                        {
                            "input": t.input,
                            "expected": expected,
                            "actual": "",
                            "status": "TLE",
                        }
                    )
                    continue

                actual = normalize(stdout)
                ok = rc == 0 and actual == expected

                results.append(
                    {
                        "input": t.input,
                        "expected": expected,
                        "actual": actual,
                        "status": "AC" if ok else "WA",
                    }
                )

                if ok:
                    passed += 1

            submission.test_result = format_test_result(
                passed,
                len(tests),
                results=results,
            )
            await db.commit()
            await finalize_submission_review_status(submission_id)
            print(f"JUDGE DONE: {passed}/{len(tests)}")
        finally:
            run(["docker", "rm", "-f", container])
            shutil.rmtree(temp_dir, ignore_errors=True)
