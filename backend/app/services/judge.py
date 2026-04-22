import subprocess
import tempfile
import os
import shutil

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.test_case import TestCase
from app.models.submission import Submission, SubmissionStatus


DOCKER_IMAGE = "judge-box"
TIMEOUT = 2


# -----------------------------
# SAFE RUN
# -----------------------------
def run(cmd, input_data=None):
    try:
        if isinstance(input_data, str):
            input_data = input_data.encode()

        p = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            timeout=TIMEOUT
        )

        return (
            p.stdout.decode(errors="ignore"),
            p.stderr.decode(errors="ignore"),
            p.returncode
        )

    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1


# -----------------------------
# CONTAINER RUN HELPERS
# -----------------------------
def docker_exec(container, cmd, input_data=None):
    return run(["docker", "exec", "-i", container] + cmd, input_data)


def compile_cpp(container, filename):
    return docker_exec(
        container,
        ["g++", filename, "-O2", "-o", "main.out"]
    )


def run_cpp(container, input_data):
    return docker_exec(
        container,
        ["./main.out"],
        input_data
    )


def run_python(container, filename, input_data):
    return docker_exec(
        container,
        ["python", filename],
        input_data
    )


# -----------------------------
# NORMALIZE
# -----------------------------
def normalize(s: str) -> str:
    return (s or "").strip().replace("\r", "")


# -----------------------------
# MAIN JUDGE
# -----------------------------
async def judge_submission(submission_id: int, code: str, task_id: int, language: str):
    print("\n🔥 JUDGE START:", submission_id)

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(TestCase).where(TestCase.task_id == task_id)
        )
        tests = result.scalars().all()

        temp_dir = tempfile.mkdtemp()
        container = f"judge_{submission_id}"

        try:
            # 1. start container
            run([
                "docker", "run", "-d", "--rm",
                "--name", container,
                DOCKER_IMAGE,
                "sleep", "30"
            ])

            # 2. write file
            filename = "main.py" if language == "python" else "main.cpp"
            filepath = os.path.join(temp_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            run([
                "docker", "cp",
                filepath,
                f"{container}:/app/{filename}"
            ])

            # -----------------------------
            # COMPILE (ONLY CPP)
            # -----------------------------
            if language == "cpp":
                out, err, rc = compile_cpp(container, filename)

                if rc != 0:
                    submission = await db.get(Submission, submission_id)
                    submission.status = SubmissionStatus.failed
                    submission.test_result = f"COMPILATION ERROR:\n{err}"
                    await db.commit()
                    return

            # -----------------------------
            # TEST RUNS
            # -----------------------------
            results = []
            passed = 0

            for t in tests:
                expected = normalize(t.output)

                if language == "python":
                    stdout, stderr, rc = run_python(container, filename, t.input)
                else:
                    stdout, stderr, rc = run_cpp(container, t.input)

                # TIMEOUT HANDLING (IMPORTANT FIX)
                if rc == -1 and stderr == "TIMEOUT":
                    results.append({
                        "input": t.input,
                        "expected": expected,
                        "actual": "",
                        "status": "TLE"
                    })
                    continue

                actual = normalize(stdout)

                ok = (rc == 0 and actual == expected)

                results.append({
                    "input": t.input,
                    "expected": expected,
                    "actual": actual,
                    "status": "AC" if ok else "WA"
                })

                if ok:
                    passed += 1

            # -----------------------------
            # SAVE RESULT
            # -----------------------------
            submission = await db.get(Submission, submission_id)

            submission.test_result = (
                f"PASSED: {passed}/{len(tests)}\n\n" +
                "\n".join(
                    f"Input: {r['input']}\n"
                    f"Expected: {r['expected']}\n"
                    f"Actual: {r['actual']}\n"
                    f"Status: {r['status']}\n"
                    "------"
                    for r in results
                )
            )

            submission.status = (
                SubmissionStatus.passed
                if passed == len(tests)
                else SubmissionStatus.failed
            )

            await db.commit()

            print("🔥 JUDGE DONE:", passed, "/", len(tests))

        finally:
            run(["docker", "rm", "-f", container])
            shutil.rmtree(temp_dir, ignore_errors=True)