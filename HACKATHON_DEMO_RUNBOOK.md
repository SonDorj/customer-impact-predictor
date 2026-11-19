<!-- AIFEL-AI-LABEL-V1: product="AIFEL Team Assistant"; origin=ai_generated -->
# Customer Impact Predictor - Live Demo Runbook

[AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]

**Team:** Quantum Forge | **Full walkthrough:** approximately 2 minutes  
**Starting point:** Python and Spring Boot are already running.

**Core message:** Identify which customer services need attention before
confirmed degradation, and explicitly withhold a forecast when evidence is missing.

This is a working API prototype, not a front-end application. Inventory
relationships are supplied; performance, alarms, maintenance and outcome labels
are synthetic. No production connection is required.

## Before recording

Use a third Windows PowerShell terminal. Leave the two service terminals running.
Increase the font size, maximize this window and close unrelated windows.
Prepare the commands in order so you are not typing long commands on camera.

```powershell
cd "C:\Users\AD35997\Downloads\hackathon data\customer-impact-predictor"
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8180"

# Prepare the normal POST request before recording.
.\.venv\Scripts\python.exe scripts/create_demo_request.py `
  --minute 150 --service-id EVC-01 --service-id EVC-12
if ($LASTEXITCODE -ne 0) { throw "Demo request preparation failed." }

# Rehearse readiness; do not record startup or dependency installation.
Invoke-RestMethod "http://127.0.0.1:8181/health"
Invoke-RestMethod "$base/actuator/health"
```

Expect Python `ready` and Spring `UP`. If either fails, fix it before recording;
do not continue as though the demo is live. The request helper overwrites
`build/demo-request.json` with bundled synthetic observations.

## 1. Prove the application is ready - 10 seconds

**Run:**

```powershell
Clear-Host
Write-Host "CUSTOMER IMPACT PREDICTOR | SYNTHETIC REPLAY"
Invoke-RestMethod "$base/actuator/health" | Format-List status
```

**Point to:** `UP`.

**Say:**

> "This is our running Spring Boot API backed by a trained Python model.
> The demonstration uses supplied inventory relationships and synthetic signals
> and outcomes."

## 2. Show the service-risk queue - 25 seconds

**Run:**

```powershell
Clear-Host
Write-Host "SERVICE RISK | SYNTHETIC REPLAY | MINUTE 150"
$result = Invoke-RestMethod "$base/api/v1/demo/predictions?minute=150"
$result.services |
  Select-Object serviceId, customerId, riskBand |
  Format-Table -AutoSize
```

**Point to:** EVC-01 through EVC-05, then EVC-09 through EVC-12.

**Say:**

> "We assess twelve Ethernet services for new degradation within the next thirty
> minutes. These five High-risk services share resource R-01 across three
> organizations. Other services receive different bands; controls are not forced
> to Low."

**Expected at minute 150:**

| Services | Band |
|---|---|
| EVC-01 through EVC-05 | High |
| EVC-06 through EVC-08 | Elevated |
| EVC-09 | Low |
| EVC-10 | Elevated |
| EVC-11 | Watch |
| EVC-12 | Insufficient evidence |

Inventory links establish association, not verified forwarding or protection.
Exact enum capitalization in the terminal may differ from the display names here.

## 3. Explain one prediction - 30 seconds

**Run:**

```powershell
Clear-Host
Write-Host "WHY EVC-01 NEEDS ATTENTION | SYNTHETIC REPLAY"
$service = $result.services | Where-Object serviceId -eq "EVC-01"
$service |
  Select-Object serviceId, riskBand, uncalibratedModelScore, heuristicScore |
  Format-List
$service.evidence |
  Select-Object latestLatencyMs, latestPacketLossPct,
    validHistoryFraction, activeAlarmMaxSeverity |
  Format-List
```

**Point to:** High, model score approximately `0.99025`, heuristic `20`,
latency approximately `66.10`, loss approximately `0.294`, history fraction `1`
and alarm severity `0`.

**Say:**

> "EVC-01 has sixty-six milliseconds of latency, zero point two nine four percent
> loss, and no active alarm. Its current values are below our simulated
> degradation thresholds. The model flags the historical pattern before those
> thresholds are breached, while the heuristic scores only twenty."

**Then explain the verified replay outcome:**

> "The confirming bad intervals begin at minute 165, fifteen minutes after this
> forecast. Confirmation occurs at 175. This is a replay result, not a guaranteed
> warning time or a calibrated ninety-nine-percent outage probability."

The evidence fields show current context, not a causal explanation of the Random
Forest. Future confirmation is evaluation ground truth, never an inference input.
Do not expect the minute-150 API response itself to contain the future timeline.

## 4. Demonstrate honest uncertainty - 15 seconds

**Run:**

```powershell
Clear-Host
Write-Host "MISSING EVIDENCE DOES NOT MEAN HEALTHY"
$result.services |
  Where-Object serviceId -eq "EVC-12" |
  Select-Object serviceId, status, reason, uncalibratedModelScore |
  ConvertTo-Json -Depth 4
```

**Point to:** insufficient evidence, the reason and the explicit `null` score.

**Say:**

> "EVC-12 exists in inventory, but required performance evidence is missing.
> We return insufficient evidence and no numeric score, rather than misleadingly
> calling it healthy."

## 5. Show normal request-based inference - 20 seconds

**Run:**

```powershell
Clear-Host
Write-Host "NORMAL POST INFERENCE | PROVIDED SYNTHETIC OBSERVATIONS"
$postResult = Invoke-RestMethod `
  -Method Post `
  -Uri "$base/api/v1/impact/predictions" `
  -ContentType "application/json" `
  -InFile "build/demo-request.json"

$postResult | Select-Object source, predictionMinute | Format-List
$postResult.services |
  Select-Object serviceId, riskBand, uncalibratedModelScore |
  Format-Table -AutoSize
```

**Point to:** `provided_synthetic_observations`, EVC-01 High and EVC-12
insufficient evidence.

**Say:**

> "This is the normal POST endpoint. We submit observation records through Spring
> Boot to the model, rather than using only the replay endpoint. It produces the
> same assessment from the same evidence, including abstention."

These are the same packaged synthetic observations, not a new independent test
or a live source integration.

## 6. Connect the result to customer action - 20 seconds

**Run:**

```powershell
Clear-Host
Write-Host "CUSTOMER PRIORITIZATION | ALL 12 REPLAY SERVICES"
$result.customers |
  Select-Object customerId,
    @{Name="Risk"; Expression={$_.riskBandAmongAssessedServices}},
    @{Name="Assessed"; Expression={$_.assessedServices}},
    @{Name="Missing"; Expression={$_.insufficientEvidenceServices}},
    @{Name="Degraded"; Expression={$_.alreadyDegradedServices}} |
  Format-Table -AutoSize
```

Use `$result`, not `$postResult`: the replay requested all twelve services; the
POST requested only two.

**Say:**

> "We roll service risk up to the associated customer, retaining missing-evidence
> and already-degraded counts. This helps prioritize investigation and targeted
> engagement. Next, we would validate warning lead time, false escalations and
> triage effort against authorized historical data."

The customer band is the highest band among assessed requested services, not a
separately trained customer probability. No automated ticketing or remediation is
implemented, and no production savings have been measured.

## Short version for the existing four-minute presentation

The full walkthrough above takes approximately two minutes and **does not fit**
inside slide 4's existing 55-second allocation. For that recording:

1. Complete setup, readiness and request preparation off camera.
2. Show step 2's service table for 15 seconds.
3. Show step 3's evidence for 25 seconds, including the synthetic timeline.
4. Show step 4's explicit null score for 15 seconds.

Skip the POST and customer-table screens in this version. Mention the customer
rollup while showing the service/customer columns. Keep the full walkthrough for
questions or a separate technical demonstration.

**55-second narration:**

> "This synthetic replay assesses twelve Ethernet services for new degradation
> within thirty minutes. Five High-risk services share one resource across three
> organizations, helping us prioritize customer investigation. At minute 150,
> EVC-01 has sixty-six milliseconds of latency, zero point two nine four percent
> loss, and no active alarm. The heuristic scores twenty, but the trained model
> identifies High risk from historical patterns. In this replay, the confirming
> bad intervals begin fifteen minutes later. The score is not a calibrated
> production probability. EVC-12 has missing required telemetry, so we explicitly
> withhold a score rather than call it healthy. Historical validation is our next
> step before production claims."

## Capture evidence without exposing unrelated information

For manual Windows screenshots, use **Win+Shift+S**, select only the relevant
terminal region, then open the capture notification and save it from Snipping
Tool. Save useful views as `01-service-risk.png`, `02-evc01-evidence.png`,
`03-insufficient-evidence.png` and `04-post-inference.png` in a dedicated local
demo folder. Keep the synthetic qualifier visible.

Screenshots are saved evidence of a run, not a live interaction. Label them as
such if used instead of the running application. Do not include credentials,
source-to-alias crosswalks, other applications or private desktop content.

For the talk, use `HACKATHON_PRESENTATION.pptx`. For implementation details and
judges' questions, use `END_TO_END_EXPLANATION.md` and the presentation's Markdown
appendix.
