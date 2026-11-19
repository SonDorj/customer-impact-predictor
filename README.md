<!-- AIFEL-AI-LABEL-V1: product="AIFEL Team Assistant"; origin=ai_generated -->
# Customer Impact Predictor

[AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]

**Global STEPN Hackathon 2026 | Quantum Forge**

Identify Ethernet services that show elevated near-term degradation risk, then
roll those services up to customers through a small, explicit inventory graph.
The prototype combines resource performance, alarms and maintenance context in a
trained Random Forest, with a transparent heuristic comparator and explicit
abstention when evidence is missing.

**This is a synthetic-only prediction POC, not a production outage predictor.**
The inventory relationships come from a supplied inventory slice; the packaged
IDs are aliases. All performance, alarms, maintenance records and outcome labels
used for training or demonstration are simulated. No live RFM, NVD/HiPer, CIIT or
Clarify access is needed to clone and run.

## What is included

- Original Python simulator, historical feature extraction, trainer and FastAPI.
- Original Spring Boot REST adapter, typed contracts and dependency health.
- The already-trained, local `run-001` model and its original evaluation/replay.
- A self-contained, alias-only inventory: **12 EVCs, 9 organization aliases,
  19 UNIs and 31 resources**.
- Locked Python packages, Maven Wrapper, Windows and POSIX startup scripts,
  unit/API/packaging tests, optional real HTTP integration test and CI definition.

There is **no front-end UI** in this repository. Swagger, HTTP requests and JSON
responses provide the runnable prototype. A UI can consume the Spring endpoints.

## Architecture

```text
Client / demo UI / curl
         |
         v
Spring Boot 3.5.8 / Java 21                         localhost:8180
  Request validation, typed REST contracts, HTTP error mapping
         |
         | HTTP, normalized observations
         v
FastAPI / Python 3.14                              localhost:8181
  As-of-time filtering -> evidence gates -> historical features
         |
         v
Trusted local Random Forest + heuristic comparator
         |
         v
Resource -> UNI -> EVC -> organization aggregation
```

Spring Boot does not implement a second model or silently invent predictions
when inference is unavailable. Python verifies local artifact hashes, the frozen
feature/inference code and scientific package versions before loading the model.
Both services listen on loopback by default.

## 1. Prerequisites

| Requirement | Purpose |
|---|---|
| Git | Clone the approved private repository |
| **Python 3.14** with `venv` and `pip` | Exact locked model environment |
| **JDK 21** | Compile and run Spring Boot |
| Internet access to approved Python/Maven package sources | Initial dependency downloads |

Maven does not need to be installed: the checked-in wrapper downloads **Maven
3.9.9**. Its small official bootstrap JAR is included so extraction uses Java,
without requiring an external `unzip` command. Maven and wrapper checksums are pinned.
Docker, database passwords, API tokens, raw source inventory and the
original author's tools are not required.

Use the native Windows commands **or** the native Linux/WSL commands consistently.
A Windows virtual environment cannot be reused as a Linux virtual environment,
and vice versa. A directory copied with an existing `.venv` is not a clean clone.

The five scientific packages must match the trained artifact exactly:
`numpy==2.5.5`, `scikit-learn==1.9.1`, `scipy==1.18.1`,
`joblib==1.6.0`, `threadpoolctl==3.8.0`. Install the full API lock file, not just
these five packages. Changing them requires deliberate retraining and validation.

## 2. Clone and set up

Use an approved **private/internal** repository URL supplied by the team:

```bash
git clone <approved-private-repository-url>
cd customer-impact-predictor
```

### Windows PowerShell

Set `JAVA_HOME` in this terminal to your own JDK 21 installation, or pass
`-JavaHome` without changing the persistent machine configuration:

```powershell
python --version
.\setup.ps1 -JavaHome "C:\path\to\your\jdk-21"
```

If `python` is not your Python 3.14 executable:

```powershell
.\setup.ps1 -PythonCommand "C:\path\to\Python314\python.exe" -JavaHome "C:\path\to\your\jdk-21"
```

The setup creates `.venv`, installs locked dependencies, builds the executable JAR
and runs the Java tests. It does not change persistent Java defaults.
If corporate execution policy blocks local PowerShell scripts, follow your
organization's approved policy; do not disable machine-wide security controls.

### Linux / WSL

Point `JAVA_HOME` at your installed Linux JDK 21 if it is not already configured:

```bash
export JAVA_HOME=/path/to/your/linux-jdk-21
PYTHON=python3.14 bash setup.sh
```

If `python3` is already Python 3.14, `bash setup.sh` is sufficient. Install missing
Python `venv`/`pip` or JDK prerequisites using your approved workstation process.

### Check the package

Windows:

```powershell
.\.venv\Scripts\python.exe scripts/verify_checkout.py
```

Linux / WSL:

```bash
.venv/bin/python scripts/verify_checkout.py
```

This checks the alias inventory, original training provenance, bundled artifact
hashes, contract, scientific dependencies and loadability of the trusted model.
It does not contact production systems.

## 3. Start both services

Run each command from the repository root in its **own terminal**. Keep the
processes in the foreground; stop them with `Ctrl+C`.

| Platform | Terminal 1: inference | Terminal 2: Spring Boot |
|---|---|---|
| Windows PowerShell | `.\start-inference.ps1` | `.\springboot-service\start.ps1 -JavaHome "C:\path\to\your\jdk-21"` |
| Linux / WSL | `bash start-inference.sh` | `bash start-backend.sh` |

On Linux/WSL, make sure terminal 2 also has the intended `JAVA_HOME`.
The backend JAR is `springboot-service/target/customer-impact-service-0.1.0.jar`.

Confirm readiness:

```bash
curl http://127.0.0.1:8181/health
curl http://127.0.0.1:8180/actuator/health
```

On Windows PowerShell use `curl.exe` instead of `curl`, because older PowerShell
aliases `curl` to a different command.

Expected: inference `status: ready`, Spring `status: UP`.
Python interactive API documentation: **http://127.0.0.1:8181/docs**.

### Optional ports and model selection

| Setting | Default | Meaning |
|---|---|---|
| `IMPACT_RUN_NAME` | `run-001` | Python model in exactly one of `models/` or `runs/` |
| `IMPACT_PORT` | `8181` | POSIX inference startup script port |
| `SERVER_PORT` | `8180` | POSIX/backend Spring port |
| `INFERENCE_BASE_URL` | `http://127.0.0.1:8181` | Spring's Python base URL |

PowerShell scripts expose explicit parameters:

```powershell
.\start-inference.ps1 -Port 8281 -RunName run-001
.\springboot-service\start.ps1 -JavaHome "C:\path\to\your\jdk-21" -Port 8280 -InferenceBaseUrl "http://127.0.0.1:8281"
```

Do not expose these unauthenticated POC services on a public/shared interface.

## 4. Run the demonstration

### Inventory and model

```bash
curl http://127.0.0.1:8180/api/v1/inventory
curl http://127.0.0.1:8180/api/v1/model
```

The inventory response supplies nodes and edges for visualization. Model metadata
includes the model ID, SHA-256, feature names, thresholds and synthetic test
metrics. No private source-to-alias crosswalk is included.

### Shared-resource replay

```bash
curl "http://127.0.0.1:8180/api/v1/demo/predictions?minute=150"
```

Select minutes `0..360`, in multiples of five. Minute **150** is the supplied
representative frame. `EVC-01` is High there; `EVC-12` has insufficient evidence
and null scores. All 12 services and the relevant customer rollups remain visible.

The neighborhood contains:

| Slice | Purpose |
|---|---|
| Resource `R-01`, five associated services across three organizations | Shared-resource fan-out |
| Resource `R-02`, three other services across two organizations | Separate neighborhood |
| `EVC-09`, `EVC-10`, `EVC-11` | Controls, isolated from the declared shared-event resources |
| `EVC-12` | Inventory present, deliberately missing current replay performance |

Control services are not hardcoded to Low. The learned score can assign Watch or
Elevated to a control; show the actual result rather than altering it for a demo.
Association edges do not establish real forwarding paths or protection.

### POST a complete observation request

The replay endpoint is convenient, but the normal inference path accepts actual
request observations rather than secretly substituting replay data.

From the repository root, generate a UTF-8 request containing the packaged
synthetic performance, alarms and feed-status records:

Windows:

```powershell
.\.venv\Scripts\python.exe scripts/create_demo_request.py --service-id EVC-01 --service-id EVC-12
curl.exe -H "Content-Type: application/json" --data-binary "@build/demo-request.json" http://127.0.0.1:8180/api/v1/impact/predictions
```

Linux / WSL:

```bash
.venv/bin/python scripts/create_demo_request.py --service-id EVC-01 --service-id EVC-12
curl -H "Content-Type: application/json" --data-binary @build/demo-request.json \
  http://127.0.0.1:8180/api/v1/impact/predictions
```

The helper overwrites its generated `build/demo-request.json`. Choose a different
`--output` path to retain another request, and `--minute` to change the as-of time.
Omit `--service-id` to request all services. The synthetic source records are
normalized, source-inspired schemas, **not verified native vendor wire formats**.

Request shape:

```json
{
  "predictionMinute": 150,
  "serviceIds": ["EVC-01"],
  "performance": [],
  "alarms": [],
  "maintenance": [],
  "feedStatus": []
}
```

That deliberately empty example returns **insufficient evidence**, not Low.
Use the helper's populated request to exercise real model inference.

| Array | Fields per record |
|---|---|
| `performance` | `resourceId`, `eventMinute`, `observedMinute`, `latencyMs`, `packetDeliveryPct`, `jitterMs` |
| `alarms` | `resourceId`, `eventMinute`, `observedMinute`, `severity` (0..3), `action` (`RAISE`/`CLEAR`) |
| `maintenance` | `resourceId`, `startMinute`, `endMinute`, `knownMinute`, `observedMinute` |
| `feedStatus` | `eventMinute`, `observedMinute`, `alarmFeedAvailable`, `maintenanceFeedAvailable` |

Minutes are relative to the simulated episode, not wall-clock production
timestamps. IDs must be inventory aliases. Records arriving after the prediction
time cannot influence the prediction. GCR-like maintenance context is supported
in training and POST requests; the packaged representative replay has no
maintenance records.

### API reference

| Spring endpoint | Corresponding Python endpoint |
|---|---|
| `GET /actuator/health` | `GET /health` |
| `GET /api/v1/model` | `GET /v1/model` |
| `GET /api/v1/inventory` | `GET /v1/inventory` |
| `GET /api/v1/demo/predictions?minute=150` | `GET /v1/demo/predictions?minute=150` |
| `POST /api/v1/impact/predictions` | `POST /v1/predictions` |

Spring returns `400` for invalid observations, `404` for an unknown service,
`502` for malformed inference responses, `503` for unavailable inference and
`504` for timeout. Direct FastAPI schema errors use `422`.
If Python stops, Spring health and prediction availability fail explicitly:
there is no success-shaped fallback and no fabricated Low prediction.

## 5. What the model predicts

### Target and timing

At prediction time `t`, estimate whether the modeled service develops a **new
confirmed degradation in `(t, t + 30 minutes]`**.

- Measurements represent completed five-minute intervals.
- A modeled bad interval has latency at least `100 ms` **or** packet loss at least
  `1%`.
- Confirmation requires **two consecutive bad intervals**. Confirmation time is
  the end of the second bad interval, not the beginning of impairment.
- Service performance is a worst-attached-resource proxy for an unprotected
  service. It is not a verified production path or protection model.
- The model looks back over six completed intervals. It does not receive future
  outcomes, scenario names, customer IDs or service IDs as predictive features.

### Evidence gates and response states

| Status | Meaning | Model score |
|---|---|---|
| `assessed` | Required evidence passes, no current confirmed degradation | Uncalibrated classifier score |
| `insufficient_evidence` | Missing/stale/invalid required performance | `null` |
| `already_degraded` | Two current observed bad intervals already confirm degradation | `null` |

Required performance coverage is at least five valid intervals of the last six
for **every** attached resource, with the newest no more than ten minutes old.
Missing optional alarm/maintenance feeds create explicit availability flags and
missing optional features, rather than pretending there were zero events.

Customer results retain assessed, missing-evidence and already-degraded service
counts. The highest assessed-service band is a summary, not a customer outage
probability, and does not erase unassessed services.

### Features, model and bands

Nineteen historical features capture performance level/trend, persistence,
coverage, alarm activity, maintenance context and source availability. Their exact
names appear in `/api/v1/model` and `models/run-001/data_dictionary.json`.

Random Forest settings: 120 trees, maximum depth 10, minimum leaf size 20,
`balanced_subsample`, sampling fraction 0.8, two worker threads.
High is selected by validation F1; Watch/Elevated use validation score quantiles
below High. These are POC bands, not independently calibrated severity classes.

| Band | `run-001` lower bound |
|---|---|
| Low | 0 |
| Watch | 0.06757793356275152 |
| Elevated | 0.11913129621612946 |
| High | 0.8125858475756745 |

Never describe a score of `0.85` as an 85% production outage probability.
The separate heuristic evidence score is a transparent comparator.
**Heuristic components are not Random Forest feature attribution.**
Maintenance is context, not an automatic risk discount.

## 6. Evaluation: actual bundled synthetic results

The original run uses 300 independent six-hour episodes: 210 training,
45 validation and 45 test. All service windows from an episode stay together.
Topology and generator family are shared across splits; this does not demonstrate
generalization to unseen networks or production.

| Held-out synthetic test metric | Random Forest | Heuristic |
|---|---:|---:|
| Precision | 0.5421 | 0.3128 |
| Recall | 0.8256 | 0.6769 |
| Average precision / PR-AUC | 0.6772 | 0.2503 |
| False alert windows | 136 | 290 |
| Service-episodes with any false alert | 46 | 44 |
| Eligible events warned before confirmation | 41 / 46 | 41 / 46 |
| Events warned before first bad interval | 39 / 46 | 35 / 46 |

There are 25,821 assessed test windows, 195 positive windows, 7,038
insufficient-evidence windows and 81 already-degraded windows.
Forecast coverage excluding already-degraded windows is approximately **78.58%**.
Median proactive lead time among proactively warned events is **15 minutes**.

Fewer false alert *windows* did **not** mean fewer service-episodes with any false
alert. Do not claim proven fewer operational escalations, measured financial
savings, real-world prediction accuracy or prevented production outages.
See `models/run-001/evaluation.json` and `heldout_predictions.csv` for details.

## 7. Train a new local experiment

Training is optional: teammates can run the packaged model immediately.
The alias-only inventory is sufficient to regenerate synthetic training data.
No private crosswalk or original inventory folder is required.

Windows:

```powershell
.\.venv\Scripts\python.exe -m impact_predictor --run-name run-002 --seed 2026
.\start-inference.ps1 -RunName run-002
```

Linux / WSL:

```bash
.venv/bin/python -m impact_predictor --run-name run-002 --seed 2026
IMPACT_RUN_NAME=run-002 bash start-inference.sh
```

The trainer simulates source tables and outcomes, extracts historical features,
fits the model, chooses thresholds on validation only, evaluates held-out
episodes, reload-checks the model and produces a separate replay.
Output goes into ignored `runs/run-002/`; expect substantially more data than the
compact bundled model. Existing names cannot be overwritten, and `run-001`
cannot shadow the bundled model.

The new run records the exported inventory manifest rather than requiring the
original private hash chain. It is a new experiment; do not claim its joblib bytes
or floating-point scores are identical to the historical run. Changing core
feature/simulation/inference code deliberately invalidates the historical model.

## 8. Tests

After setup, run the focused Python unit/API/packaging suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

On Linux/WSL replace the executable with `.venv/bin/python`.
The real HTTP integration test is skipped unless explicitly enabled.

Java tests/build:

```powershell
.\springboot-service\build.ps1 -JavaHome "C:\path\to\your\jdk-21"
```

```bash
cd springboot-service
./mvnw -B -ntp -s maven-settings.xml package
cd ..
```

Opt-in real service integration, after building the JAR:

```powershell
$env:RUN_STACK_INTEGRATION = "1"
$env:JAVA_HOME = "C:\path\to\your\jdk-21"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_stack_integration.py -v
Remove-Item Env:RUN_STACK_INTEGRATION
```

```bash
RUN_STACK_INTEGRATION=1 .venv/bin/python -m unittest discover -s tests -p test_stack_integration.py -v
```

This test starts its own Python and Java processes on temporary loopback ports,
checks actual replay and POST parity, abstention, validation, unknown service and
Python-offline failures, then stops only the processes it owns. Running your demo
servers separately is not required.

The GitHub Actions definition runs Python, Java and real-stack checks on Linux and
Windows when pushed to an approved repository. Adding the workflow does not mean
remote CI has already executed.

## 9. Repository layout and provenance

```text
impact_predictor/             Simulator, features, training, inference, API
data/inventory/               Alias-only topology and input checksums
models/run-001/               Trusted historical model and compact replay
  package_manifest.json      Export scope and integrity/provenance chain
  training_manifest.json     Unchanged original training manifest
  training_inventory_manifest.json
                             Unchanged hash-only original inventory provenance
springboot-service/          Java source, tests and Maven Wrapper
scripts/                     Verification and request-generation utilities
tests/                       Python unit/API/packaging/integration tests
approved_contract.json       Frozen target and training contract
requirements-api.lock.txt    Exact inference/training/test dependencies
README.md                    Setup, explanation and demonstration
runs/                        New generated experiments; ignored by Git
```

The original training manifests contain historical filenames and hashes for
inputs that are deliberately **not** distributed. Those historical paths are
metadata, not runtime dependencies. The export independently verifies the eight
bundled alias inventory files against the original provenance, and preserves the
original model/evaluation bytes.

Original raw inventories, source-to-alias crosswalks, connection profiles,
credentials, Bruno collections, virtual environments, installed JDK/Maven tools,
reference checkout, compiled application JARs and full generated training tables
are excluded. The official Maven Wrapper bootstrap JAR is the documented
third-party tooling exception, covered by its included Apache license.
Source inventory associations and company-derived artifacts still require an
approved internal distribution channel; aliases are not permission to publish
publicly. Never upload an untrusted `.joblib`: Python pickle formats can execute
code, and a hash is an integrity check, not an independent authenticity guarantee.

**Scanner note:** the unchanged official Apache `mvnw` script reads the
`MVNW_PASSWORD` environment variable in an optional authenticated-download branch.
The local assistant scanner misclassifies that expansion as a hardcoded password.
It is a verified upstream false positive, not a bundled credential. The wrapper
has not been modified or suppressed to hide the finding; review any new findings.

Architectural inspiration:
[ML priority classifier example](https://github.com/jbossramana/AI_Powered_Modern_Microservices_Architecture_Customer_Support/tree/main/06.4-ml-priority-classifier).
No implementation or model artifact from that example is redistributed here.
See [NOTICE.md](NOTICE.md) for distribution and third-party notices.

## 10. Prepare the first push

Review the staged content and obtain an approved **private** remote URL. The
prepared local repository has no configured origin and has not been published.
If using the ZIP rather than the prepared Git folder, initialize it first:

```bash
git init -b main
git add .
git diff --cached --stat
```

After your review, create the initial commit, replace the remote placeholder and
push:

```bash
git commit -m "Package Customer Impact Predictor hackathon POC" -m "AI-Generated-By: AIFEL Team Assistant vv1.0.2" -m "AI-Label-Version: 1" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git remote add origin <approved-private-repository-url>
git push -u origin main
```

Do not push raw inventory, credentials, `.venv`, `target`, `runs` or the original
workspace. The `.gitattributes` rules preserve hash-sensitive data/model bytes and
core Python line endings even on Windows.

## Troubleshooting

| Symptom | Action |
|---|---|
| Python version/locked dependency mismatch | Recreate `.venv` using Python 3.14 and the complete API lock file |
| Windows Python script looks for Linux `.venv/bin` | Use the Windows setup/start commands; do not copy a WSL environment |
| `release version 21 not supported` | Select JDK 21 for this terminal or pass `-JavaHome` |
| Maven Wrapper cannot download Maven | Check approved network/proxy/certificate configuration; do not disable TLS validation |
| Corporate Maven settings interfere | Supplied build scripts use the credential-free project `maven-settings.xml`; configure approved proxies locally if needed |
| Python fails artifact integrity check | Restore the intended Git files with your normal review process; do not edit checksums just to suppress an error |
| Spring health `DOWN` / prediction `503` | Start Python and verify the configured base URL/port |
| Prediction `insufficient_evidence` | Supply complete, recent observations for every attached resource; not an API failure |
| Existing service is `already_degraded` | This is current degradation, not a future-onset prediction |
| An unaffected control is Watch/Elevated | Genuine uncalibrated model behavior; do not hardcode a nicer result |
| FastAPI TestClient httpx deprecation warning | Non-failing warning in the frozen environment; do not casually upgrade trained-model dependencies |

## Four-minute video outline

1. **0:00-0:35 - Business problem:** resource alarms do not directly prioritize
   which customers may soon experience degradation.
2. **0:35-1:10 - Approach:** inventory correlation plus recent evidence,
   simulation-trained forecasting and explicit missing-data handling.
3. **1:10-2:40 - Prototype:** show model identity and neighborhood; replay shared
   resource fan-out; POST observations; contrast a control and EVC-12 abstention.
4. **2:40-3:25 - Evidence:** synthetic held-out precision/recall, coverage and
   proactive lead time, including false-alert and generalization limitations.
5. **3:25-4:00 - Next validation:** authorized source adapters, real historical
   outcomes, temporal backtesting and shadow operation before business-impact
   claims. Present reduced triage time and earlier engagement as hypotheses to
   measure, not savings already delivered.
