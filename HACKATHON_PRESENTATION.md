<!-- AIFEL-AI-LABEL-V1: product="AIFEL Team Assistant"; origin=ai_generated -->
# Customer Impact Predictor - Hackathon Presentation

[AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]

**Team:** Quantum Forge  
**Event:** Global STEPN Hackathon 2026  
**Format:** Seven slides, four-minute video  
**Positioning:** Supplied inventory relationships, synthetic signals and outcomes,
and a genuinely trained predictor. Not a production-validated forecasting system.

## Running order

| Slide | Topic | Duration | Video time |
|---|---|---:|---|
| 1 | Business problem and promise | 25 sec | 0:00-0:25 |
| 2 | Customer-impact neighborhood | 35 sec | 0:25-1:00 |
| 3 | Data-to-prediction pipeline and safeguards | 35 sec | 1:00-1:35 |
| 4 | Verified prototype replay | 55 sec | 1:35-2:30 |
| 5 | Measured synthetic evaluation | 40 sec | 2:30-3:10 |
| 6 | Business-value validation plan | 30 sec | 3:10-3:40 |
| 7 | Team and closing request | 20 sec | 3:40-4:00 |

Use the editable PowerPoint for delivery or the PDF for a static presentation.
The same speaker scripts are embedded in the PowerPoint notes. The deck stores
the proposed durations; rehearse manually before using automatic timings.

## Slide 1: Know which customers may be next

**Time:** 0:00-0:25, 25 seconds.

### On-screen message

Customer Impact Predictor

**From network signals to earlier customer action.**

Resource symptoms do not automatically reveal which customer services need
attention. Connect the signals to a customer-level risk queue.

### Speaker script

Network signals tell us that a resource is behaving differently. The operational
question is: which customer services could be affected next, and where should we
focus attention? Quantum Forge connects inventory relationships with recent
performance, alarms and maintenance context to forecast new service degradation
within thirty minutes, then roll that risk up to customers.

### Presenter actions

Lead with the customer and triage problem, not the model or programming language.
Do not claim measured production savings or incident prevention.

## Slide 2: One resource. Several services. Multiple customers.

**Time:** 0:25-1:00, 35 seconds.

### On-screen message

```text
                  Shared resource R-01
                           |
        +----------+-------+-------+----------+
        |          |       |       |          |
      EVC-01    EVC-02   EVC-03   EVC-04    EVC-05
        |          |       |       |          |
      Org-A      Org-B   Org-B   Org-B      Org-C
```

Qualified inventory: 2,595 EVCs. Demonstration slice: 12 EVCs, 9 organization
aliases, 31 resources. Inventory associations are not verified forwarding paths.

### Speaker script

We started with supplied Ethernet inventory and qualified two thousand five
hundred ninety-five EVC services. We selected twelve services with meaningful
relationships, rather than a random sample. Here, one shared resource maps to five
services across three organizations. A second neighborhood, three controls and
one missing-evidence service let us demonstrate fan-out, separation and
abstention. Both service endpoints are preserved. These are inventory
associations, not verified forwarding paths.

### Presenter actions

Point from R-01 to the five services, then to the three distinct organizations.
The graph is a genuine selected inventory neighborhood with aliased identifiers.
Do not call five services five distinct customers.

## Slide 3: A forecast that earns trust

**Time:** 1:00-1:35, 35 seconds.

### On-screen message

```text
Clean inventory -> Simulate episodes -> Learn historical patterns -> Serve risk
```

- Supplied relationships; simulated performance, alarms, maintenance and outcomes.
- 300 six-hour episodes; training, validation and test separated by whole episode.
- A trained Random Forest, not an LLM and not a copy of the heuristic.
- Missing required performance means no forecast, not Low risk.

### Speaker script

Our source discovery did not establish aligned historical signals and incident
labels, so we do not claim production training. We generated three hundred
six-hour episodes over the supplied topology. Nineteen historical features feed a
Random Forest, with whole episodes held out for evaluation. Only information
available at prediction time is used. Missing required performance produces no
score; an already-degraded service is separated from a future-onset forecast.

### Presenter actions

Say "synthetic signals and outcomes" clearly. Explain that missing optional feeds
are explicitly flagged; missing required performance is not imputed into health.
The target is new confirmed degradation in the next 30 minutes.

## Slide 4: Warning before the threshold is breached

**Time:** 1:35-2:30, 55 seconds.

### On-screen message

**Verified replay: EVC-01 at minute 150**

| Evidence | Actual replay value |
|---|---:|
| Latest latency | 66.10 ms |
| Latest packet loss | 0.294% |
| Current active alarm severity | 0 |
| Complete historical intervals | 6/6 |
| Heuristic evidence score | 20/100 |
| Random Forest band | High |
| Uncalibrated model score | 0.99025 |

```text
150                 165        170        175
 |                   |----------|----------|
Forecast High           Confirming bad intervals
                                            |
                                     Confirmation
```

15 minutes before the confirming bad intervals begin; 25 minutes before
confirmation. This is a synthetic replay, not live production.

### Speaker script

At replay minute one hundred fifty, EVC-01 has sixty-six milliseconds of latency,
zero point two nine four percent loss, and no active alarm. Neither degradation
threshold is breached. The heuristic scores twenty, below its alert threshold.
The trained model returns High from the historical feature pattern. The
simulator confirms degradation at minute one hundred seventy-five, with the
confirming bad intervals beginning at one hundred sixty-five. That is fifteen
minutes of proactive warning in this replay. Shared-resource services are
visible together. EVC-12 has missing telemetry and receives no numeric score.
The model score is not a production outage probability.

### Presenter actions

If the local services are already running, open:

`http://127.0.0.1:8180/api/v1/demo/predictions?minute=150`

Show `EVC-01`, the shared-resource services, and `EVC-12`. Return to the deck
within the slide's 55 seconds. Do not start services during the recording.

If switching to the API would interrupt the recording, use the verified replay
values already displayed in the deck; label the demonstration as a replay, not a
live production view.

Control results at this frame are EVC-09 Low, EVC-10 Elevated and EVC-11 Watch.
They are not forced to Low. The future confirmation timeline is evaluation
ground truth, not an input supplied to inference.

## Slide 5: Evidence, not inflated accuracy

**Time:** 2:30-3:10, 40 seconds.

### On-screen message

**Held-out synthetic test: 45 episodes, 25,821 assessed service-windows**

| Metric | Random Forest | Heuristic |
|---|---:|---:|
| Precision | 54.2% | 31.3% |
| Recall | 82.6% | 67.7% |
| False-alert windows | 136 | 290 |
| Service-episodes with any false alert | 46 | 44 |

Forecast coverage: 78.6%, excluding already-degraded windows. Median proactive
lead: 15 minutes among proactively warned service events.

### Speaker script

On forty-five held-out synthetic episodes, the model achieves fifty-four percent
precision and eighty-three percent recall, compared with thirty-one and
sixty-eight percent for the heuristic. Forecast coverage is seventy-nine percent.
Median proactive lead is fifteen minutes among proactively warned events.
False-alert windows fall from two hundred ninety to one hundred thirty-six.
However, service-episodes with any false alert are forty-six versus forty-four.
We therefore claim fewer false-alert windows, not proven fewer operational
escalations. These results remain simulation-domain evidence.

### Presenter actions

Keep the synthetic qualifier visible. Do not present precision as overall
accuracy, forecast coverage as recall, or lead time as a guarantee for every event.
Rows and events are service-level and can be correlated through shared resources.

## Slide 6: From alerts to earlier customer action

**Time:** 3:10-3:40, 30 seconds.

### On-screen message

**Operational workflow:** Prioritize -> investigate -> engage.

**Value hypotheses to measure:**

- Less time mapping resource symptoms to customer services.
- Useful warning before degradation.
- Acceptable distinct false-escalation burden.
- Visible assessment coverage and missing evidence.

Next gate: authorized historical alignment, temporal backtesting, then shadow
triage on one Ethernet cohort.

### Speaker script

The business opportunity is earlier, better-targeted triage: identify exposed
services, investigate the common resource, and prepare customer engagement. We
have not measured savings or prevented outages. Our next gate is authorized
historical data alignment and temporal backtesting, followed by shadow triage.
We would measure time to identify affected services, useful lead time, distinct
false escalations and evidence coverage before considering production use.

### Presenter actions

Frame benefits as testable hypotheses. No automated remediation or ticket
creation is implemented. An independently integrated change/deployment feed and
verified routing/protection behavior remain outside the current POC.

## Slide 7: Earlier context. Clearer decisions.

**Time:** 3:40-4:00, 20 seconds.

### On-screen message

**Customer Impact Predictor**

Supplied topology. Learned signals. Explicit uncertainty.

**Next step:** Validate one Ethernet cohort before expanding.

**Quantum Forge**

Sonam Dorji; Hanamantha Bhimappa; Shamanth Kumara; Tanmay Pal;
Pratap Mysore Narasimha Raju.

### Speaker script

Quantum Forge has built a runnable Spring Boot and Python prototype that connects
service risk to customers, while making missing evidence visible. Our next step
is to validate one Ethernet cohort against authorized historical outcomes before
expanding. Earlier customer context, clearer operational decisions. Thank you.

### Presenter actions

End on the practical validation request. Do not call the model production-ready.

## Appendix: Recording and demo checklist

- Use the slide show in 16:9 format and rehearse the four-minute running order.
- Start the Python and Spring Boot services before recording if using the API.
- Open the replay endpoint in a separate tab and format the JSON for readability.
- Show only aliased data. Do not expose source crosswalks, credentials or other
  application windows.
- Display the synthetic-data qualifier during the model demonstration and results.
- Do not describe the 0.99025 score as a 99% real-world outage probability.
- Do not claim a dedicated application UI; the implemented prototype exposes APIs.
- Do not claim financial savings, outage prevention or fewer operational
  escalations have been measured.
- Use approved internal distribution for the company-derived presentation.

## Appendix: Judge questions

| Question | Factual answer |
|---|---|
| Is this trained on real incident history? | No. Relationships come from supplied inventory; signals and outcome labels are synthetic. |
| Is it just a rules engine? | No. A Random Forest learns from historical features and future simulator outcomes. The heuristic is a separate comparator. |
| Why not report accuracy? | Positive windows are rare. Always predicting no degradation would yield about 99.24% test accuracy while detecting none. |
| Can it predict without telemetry? | Missing required performance produces insufficient evidence and null scores. Missing optional feeds are explicitly represented. |
| Is the score a calibrated probability? | No. It is an uncalibrated simulation-trained classifier output. |
| Does inventory prove the actual traffic path? | No. Resource exposure is based on inventory associations and an unprotected-service simulation assumption. |
| Have operational escalations decreased? | Not established. False-alert windows decreased, but service-episodes with any false alert did not. |
| Is the replay part of training? | No. It is a separate scripted demonstration episode, with its representative frame selected for presentation. |
| What does the customer result mean? | Highest band among assessed requested services, with missing-evidence and already-degraded counts retained. |
| What must happen before production claims? | Authorized real-data alignment, reliable historical labels, temporal validation and controlled shadow operation. |

## Source of figures

Inventory counts: local `clean-inventory/quality_report.json` and packaged
`data/inventory/`. Evaluation: `models/run-001/evaluation.json`. Demonstration:
verified minute-150 inference from the bundled model and its separate replay;
confirmation time reproduced using the frozen simulator and original demo seed.

The detailed technical narrative is in `END_TO_END_EXPLANATION.md`.
