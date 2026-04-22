import asyncio
import tempfile
import os
import shutil
import uuid

DOCKER_TIMEOUT = 3  # секунды


async def run_tests(code: str, language: str, tests: list[dict]):
    temp_dir = tempfile.mkdtemp(prefix="submission_")
    filename = "main.py" if language == "python" else "main.cpp"
    filepath = os.path.join(temp_dir, filename)

    # записываем код
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    container_name = f"runner_{uuid.uuid4().hex[:8]}"
    results = []

    try:
        if language == "python":
            image = "python:3.11-slim"
            run_cmd = f"python {filename}"

        elif language == "cpp":
            image = "gcc:12"

            # компиляция
            compile_process = await asyncio.create_subprocess_shell(
                f"""
                docker run --rm \
                --network none \
                --memory 128m \
                --cpus 0.5 \
                -v {temp_dir}:/app \
                -w /app \
                {image} \
                g++ {filename} -O2 -o main
                """,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await compile_process.communicate()

            if compile_process.returncode != 0:
                return [{
                    "error": "Compilation Error",
                    "details": stderr.decode()
                }]

            run_cmd = "./main"

        else:
            raise ValueError("Unsupported language")

        # прогон тестов
        for test in tests:
            try:
                process = await asyncio.create_subprocess_shell(
                    f"""
                    docker run --rm -i \
                    --network none \
                    --memory 128m \
                    --cpus 0.5 \
                    --pids-limit 64 \
                    --read-only \
                    -v {temp_dir}:/app \
                    -w /app \
                    {image} {run_cmd}
                    """,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input=test["input"].encode()),
                        timeout=DOCKER_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    results.append({
                        "input": test["input"],
                        "status": "TLE",
                        "passed": False
                    })
                    continue

                if process.returncode != 0:
                    results.append({
                        "input": test["input"],
                        "status": "RE",
                        "error": stderr.decode(),
                        "passed": False
                    })
                    continue

                output = stdout.decode().strip()
                expected = test["output"].strip()

                results.append({
                    "input": test["input"],
                    "expected": expected,
                    "actual": output,
                    "status": "OK" if output == expected else "WA",
                    "passed": output == expected
                })

            except Exception as e:
                results.append({
                    "input": test["input"],
                    "status": "ERROR",
                    "error": str(e),
                    "passed": False
                })

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return results