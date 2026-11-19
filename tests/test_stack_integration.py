"""Opt-in native Windows/Linux HTTP test; owns and stops both server processes."""

from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from impact_predictor.api import PredictorService
from impact_predictor.api_models import PredictionRequest


ROOT = Path(__file__).resolve().parents[1]


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def request(base, path, body=None):
    encoded = None if body is None else json.dumps(body).encode("utf-8")
    call = urllib.request.Request(
        base + path, data=encoded, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(call, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        with error:
            return error.code, json.load(error)


def wait_ready(process, base, path, log):
    for _ in range(240):
        if process.poll() is not None:
            log.seek(0)
            raise AssertionError("Server exited during startup:\n" + log.read()[-4000:])
        try:
            status, body = request(base, path)
            if status == 200:
                return body
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.25)
    log.seek(0)
    raise AssertionError("Server readiness timed out:\n" + log.read()[-4000:])


@unittest.skipUnless(os.environ.get("RUN_STACK_INTEGRATION") == "1",
                     "Set RUN_STACK_INTEGRATION=1 after building the Java JAR")
class FullStackTests(unittest.TestCase):
    def test_real_native_stack_and_dependency_failure(self):
        jar = ROOT / "springboot-service/target/customer-impact-service-0.1.0.jar"
        self.assertTrue(jar.is_file(), "Build Spring Boot with the Maven Wrapper first")
        if os.environ.get("JAVA_HOME"):
            java = str(Path(os.environ["JAVA_HOME"]) / "bin" /
                       ("java.exe" if os.name == "nt" else "java"))
        else:
            java = shutil.which("java")
        self.assertTrue(java and Path(java).is_file(), "A JDK 21 java executable is required")
        with socket.socket() as first, socket.socket() as second:
            first.bind(("127.0.0.1", 0))
            second.bind(("127.0.0.1", 0))
            inference_port, backend_port = first.getsockname()[1], second.getsockname()[1]
        inference_url = f"http://127.0.0.1:{inference_port}"
        backend_url = f"http://127.0.0.1:{backend_port}"
        with tempfile.TemporaryDirectory(prefix="predictor-stack-") as directory:
            with (Path(directory) / "inference.log").open("w+", encoding="utf-8") as python_log, (
                Path(directory) / "backend.log"
            ).open("w+", encoding="utf-8") as java_log:
                processes = []
                try:
                    inference = subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "impact_predictor.api:app",
                         "--host", "127.0.0.1", "--port", str(inference_port),
                         "--workers", "1", "--no-access-log"],
                        cwd=ROOT, stdout=python_log, stderr=subprocess.STDOUT,
                        env={**os.environ, "IMPACT_RUN_NAME": "run-001",
                             "OPENBLAS_NUM_THREADS": "2", "OMP_NUM_THREADS": "2"},
                    )
                    processes.append(inference)
                    health = wait_ready(inference, inference_url, "/health", python_log)
                    self.assertEqual(health["modelId"], "run-001")
                    backend = subprocess.Popen(
                        [java, "-XX:ActiveProcessorCount=2", "-Xmx384m", "-jar", str(jar),
                         "--server.address=127.0.0.1", f"--server.port={backend_port}",
                         f"--impact.inference.base-url={inference_url}"],
                        cwd=ROOT, stdout=java_log, stderr=subprocess.STDOUT,
                    )
                    processes.append(backend)
                    self.assertEqual(
                        wait_ready(backend, backend_url, "/actuator/health", java_log)["status"],
                        "UP",
                    )
                    status, metadata = request(backend_url, "/api/v1/model")
                    self.assertEqual(status, 200)
                    self.assertEqual(metadata["modelSha256"], health["modelSha256"])
                    status, inventory = request(backend_url, "/api/v1/inventory")
                    self.assertEqual(status, 200)
                    self.assertTrue(inventory["nodes"])
                    status, replay = request(
                        backend_url, "/api/v1/demo/predictions?minute=150",
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(len(replay["services"]), 12)
                    expected = {row["serviceId"]: row for row in replay["services"]}
                    self.assertEqual(expected["EVC-01"]["riskBand"], "High")
                    self.assertIsNone(expected["EVC-12"]["uncalibratedModelScore"])
                    predictor = PredictorService()
                    body = PredictionRequest(
                        prediction_minute=150, service_ids=["EVC-01", "EVC-12"],
                        performance=[asdict(row) for row in
                                     predictor.replay["hiper_performance"]],
                        alarms=[asdict(row) for row in predictor.replay["rfm_alarms"]],
                        feed_status=[asdict(row) for row in predictor.replay["feed_status"]],
                    )
                    status, provided = request(
                        backend_url, "/api/v1/impact/predictions",
                        json.loads(body.model_dump_json(by_alias=True)),
                    )
                    self.assertEqual(status, 200, provided)
                    self.assertEqual(provided["source"], "provided_synthetic_observations")
                    for row in provided["services"]:
                        score = expected[row["serviceId"]]["uncalibratedModelScore"]
                        if score is None:
                            self.assertIsNone(row["uncalibratedModelScore"])
                        else:
                            self.assertAlmostEqual(row["uncalibratedModelScore"], score, places=12)
                    status, missing = request(
                        backend_url, "/api/v1/impact/predictions",
                        {"predictionMinute": 150, "serviceIds": ["EVC-01"]},
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(missing["services"][0]["status"], "insufficient_evidence")
                    self.assertIsNone(missing["services"][0]["uncalibratedModelScore"])
                    self.assertEqual(request(
                        backend_url, "/api/v1/impact/predictions", {"predictionMinute": 151},
                    )[0], 400)
                    self.assertEqual(request(
                        backend_url, "/api/v1/impact/predictions",
                        {"predictionMinute": 150, "serviceIds": ["EVC-99"]},
                    )[0], 404)
                    stop(inference)
                    self.assertEqual(request(
                        backend_url, "/api/v1/demo/predictions?minute=150",
                    )[0], 503)
                    self.assertEqual(request(backend_url, "/actuator/health")[0], 503)
                finally:
                    for process in reversed(processes):
                        stop(process)


if __name__ == "__main__":
    unittest.main()
