import asyncio
import tempfile
import os
import shutil

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.test_case import TestCase
from app.models.submission import Submission


# -------------------------
# utils
# -------------------------
def normalize(s: str) -> str:
    return s.strip().replace("\r", "")


async def run_python(file_path: str, input_data: str):
    proc = await asyncio.create_subprocess_exec(
        "python",
        file_path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate(input=input_data.encode())

    return stdout.decode(), stderr.decode(), proc.returncode


# -------------------------
# MAIN JUDGE FUNCTION
# -------------------------
async def judge_submission(submission_id: int, code: str, task_id: int):
    print("\n🔥 JUDGE START:", submission_id)

    async with AsyncSessionLocal() as db:

        # 1. load tests
        result = await db.execute(
            select(TestCase).where(TestCase.task_id == task_id)
        )
        tests = result.scalars().all()

        # 2. temp file
        temp_dir = tempfile.mkdtemp(prefix="judge_")
        file_path = os.path.join(temp_dir, "main.py")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

        results = []
        passed = 0

        try:
            # 3. run tests
            for t in tests:
                print("🧪 TEST:", t.input)

                out, err, code_ret = await run_python(file_path, t.input)

                actual = normalize(out)
                expected = normalize(t.output)

                ok = (actual == expected) and code_ret == 0

                if ok:
                    passed += 1

                results.append({
                    "input": t.input,
                    "expected": expected,
                    "actual": actual,
                    "status": "OK" if ok else "WA"
                })

            # 4. save result
            submission = await db.get(Submission, submission_id)

            submission.test_result = str({
                "passed": passed,
                "total": len(tests),
                "results": results
            })

            submission.status = "analyzing"

            await db.commit()

            print("🔥 JUDGE DONE:", passed, "/", len(tests))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
