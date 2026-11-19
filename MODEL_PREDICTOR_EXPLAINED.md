<!-- AIFEL-AI-LABEL-V1: product="AIFEL Team Assistant"; origin=ai_generated -->
# Customer Impact Predictor - Detailed Model Explanation

[AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]

**Team:** Quantum Forge  
**Event:** Global STEPN Hackathon 2026  
**Scope:** The implemented inventory-linked, synthetic-data prediction POC.

## 1. What the predictor actually predicts

The model answers:

> Given what we know about a service now and over the recent past, will it
> experience a new confirmed degradation within the next 30 minutes?

It predicts at the **Ethernet service/EVC level**, then connects those results
to customer organizations through inventory relationships.

It does not directly predict customer complaints, churn, revenue loss or the
exact cause of an outage.

| Approach | Question |
|---|---|
| Threshold monitoring | Is the service breaching a limit now? |
| Our predictor | Does the recent pattern suggest degradation may occur soon? |
| Inventory correlation | Which services and customers are associated with the relevant resources? |

Our POC combines the last two: **learned early-warning patterns plus customer
context**.

## 2. Why inventory is the foundation

A network measurement is not useful for customer prioritization until we know
which services are associated with the measured resource.

Our relationship chain is:

```text
Network resource
       |
       v
UNI / service endpoint
       |
       v
EVC / Ethernet service
       |
       v
Customer organization
```

We cleaned the supplied inventory to retain usable relationships, checking
endpoint existence, customer consistency, active status and resource mappings.

This produced **2,595 qualified EVCs**. The demonstration uses a smaller, aliased
neighborhood containing:

- **12 services**
- **9 customer-organization aliases**
- **31 resources**

The selection deliberately includes shared resources, separate neighborhoods,
controls and one service with missing telemetry.

For example, R-01 is associated with EVC-01 through EVC-05 across three
organizations. A deteriorating shared resource can therefore create exposure
across several services.

**Limitation:** Inventory association does not establish the actual traffic path
or protection behavior. The simulator uses a simplified, unprotected-resource
exposure assumption.

## 3. Where the training data comes from

The inventory relationships are supplied, but **the measurements, alarms,
maintenance events and degradation outcomes used by the model are synthetic**.

Our source discovery did not establish sufficiently aligned historical signals
and reliable service-outcome labels for production training. Rather than claim
otherwise, we built a simulator.

It creates **300 independent six-hour episodes**, with measurements every
**five minutes**.

| Scenario | What it helps the model encounter |
|---|---|
| Healthy variation | Normal fluctuations that should not automatically trigger alerts |
| Gradual deterioration | Performance worsening before a breach |
| Intermittent faults | Unstable behavior and temporary problems |
| Expected maintenance effects | Performance changes with maintenance context |
| Unexpected deterioration during maintenance | Maintenance does not automatically mean safe |
| Missing or stale evidence | Incomplete observations and uncertainty |

The simulator creates underlying resource behavior, then produces imperfect
observations, including delayed or missing measurements.

**The model does not receive the simulator's hidden stress, scenario name or
future outcome as an input.** It receives only the historical evidence available
at prediction time.

This demonstrates a working learning pipeline, but it does not prove that the
simulator captures real network behavior accurately.

## 4. How we define the outcome to learn

A supervised model needs both:

- **Inputs:** What was observable before the prediction.
- **Labels:** What happened afterward.

In our simulation, a five-minute interval is considered bad when either:

```text
Latency >= 100 milliseconds
             OR
Packet loss >= 1%
```

Degradation is **confirmed after two consecutive bad intervals**.

For a prediction at minute 150, the label asks whether a new confirmation occurs:

```text
After minute 150 and at or before minute 180
```

If it does, the training label is `1`; otherwise, it is `0`.

These are **POC definitions**, not universal Ethernet SLA definitions.

The target is future **confirmation**. A forecast before confirmation is not
necessarily a forecast before the first bad interval. That is why we separately
measure genuinely proactive warning.

## 5. How raw observations become model inputs

The model does not consume raw API responses directly. We first convert
observations into a fixed set of **19 numerical features**.

For each service, we inspect approximately the last **30 minutes** of evidence.

When a service is associated with multiple resources, the POC constructs a
conservative performance proxy using the maximum latency, loss and jitter across
its associated resources at each interval.

These maxima may come from different resources. They are a simplified exposure
proxy, not a measured end-to-end traffic path.

### The 19 features

| Category | Features |
|---|---|
| Latency: 5 | Latest, mean, maximum, standard deviation, slope |
| Packet loss: 4 | Latest, mean, maximum, slope |
| Jitter: 1 | Latest jitter |
| Recent breaches: 1 | Number of bad historical intervals |
| Alarms: 3 | Maximum active severity, recent alarm raises, feed availability |
| Maintenance: 3 | Active maintenance, maintenance starting within 30 minutes, feed availability |
| Evidence quality: 2 | Valid-history fraction, age of newest complete observation |

These features describe more than the current value.

For example, two services could both have **66 ms latency**, but have very
different histories:

```text
Service A: 65 -> 66 -> 65 -> 66 -> 65 -> 66
Service B: 20 -> 27 -> 35 -> 44 -> 55 -> 66
```

Service A is stable. Service B is worsening.

The latest measurement alone looks similar, but their **slope, variability, mean
and maximum** differ. The model can learn associations between those patterns
and later degradation.

This sequence is an illustration, not the actual EVC-01 replay history.

## 6. Evidence checks happen before prediction

We do not score every request blindly.

### Missing or stale required telemetry

The service needs:

- At least **five of the last six complete, valid intervals**.
- Each counted interval must contain valid performance for **all associated resources**.
- The newest complete interval must be no more than **10 minutes old**.

If these conditions fail:

```text
Status: Insufficient evidence
Model score: null
```

We do not replace missing required telemetry with healthy-looking values.

### Already-degraded services

If the current and preceding intervals are both observed as bad, the service is
classified as:

```text
Already degraded
```

It does not receive a future-onset score. An existing problem should not be
presented as a successful prediction of a new one.

### Missing optional feeds

Alarm and maintenance feeds are optional context. When unavailable, their
features remain missing and availability flags indicate that condition.

The training pipeline uses **training-set median imputation plus missing-value
indicators** for these model inputs.

This is different from pretending that an unavailable alarm feed contains zero
alarms.

## 7. What the Random Forest learns

The predictor is a **Random Forest classifier containing 120 decision trees**.

A decision tree learns a sequence of questions about the feature values.
Conceptually:

```text
Is latency increasing?
       |
       v
Is variability elevated?
       |
       v
Are loss or alarm patterns concerning?
       |
       v
How often did similar training examples precede degradation?
```

Those are illustrative questions, not the literal extracted logic of a
particular tree.

Different trees learn different combinations of relationships using randomized
training samples and candidate features.

For a new service assessment:

1. Its feature vector passes through each tree.
2. Each tree produces an estimated positive-class likelihood from its reached leaf.
3. The forest averages those estimates into a score.

**It is not simply "119 trees voted outage, therefore 99% probability."**

The implementation limits tree depth to **10** and requires at least **20
training examples per leaf**, helping reduce overly specific rules. Class
balancing helps the model learn the rarer future-degradation cases.

The model is trained offline. **Calling the API does not retrain it.**

## 8. How training and evaluation are separated

We split data by **whole episode**:

| Split | Episodes | Purpose |
|---|---:|---|
| Training | 210 | Learn the model and imputation values |
| Validation | 45 | Select alert thresholds and bands |
| Test | 45 | Evaluate the frozen choices |

This matters because adjacent five-minute windows are highly related. Randomly
scattering windows from one episode across training and testing would make the
evaluation less trustworthy.

Whole-episode separation reduces that overlap.

However, all splits still use the **same inventory topology and simulator
family**. The test therefore measures generalization to held-out simulated
episodes, not to new production networks.

We also enforce **as-of-time filtering**:

> A measurement must both belong to the relevant time period and have been
> received by the prediction time.

A late-arriving observation cannot retrospectively improve an earlier
prediction. Similarly, future maintenance is usable only if the schedule was
already known and received.

## 9. How the score becomes a risk band

The model produces a score between zero and one.

The bundled thresholds are approximately:

| Score range | Band |
|---|---|
| Below 0.06758 | Low |
| 0.06758 to below 0.11913 | Watch |
| 0.11913 to below 0.81259 | Elevated |
| 0.81259 and above | High |

These rounded values are explanatory; inference uses the full-precision
thresholds in the bundled artifact.

These are **not equal-width probability bands**.

The High threshold was selected on validation data using F1, which balances
precision and recall. The lower boundaries came from validation-score quantiles
below High.

Therefore:

- Low does not guarantee health.
- High does not guarantee degradation.
- A score of `0.99` does not establish a 99% production outage probability.

The score is an **uncalibrated simulation-domain classifier output**.

## 10. Why we also show a heuristic score

We implemented a separate rules-based comparator:

| Condition | Points |
|---|---:|
| Current telemetry anomaly | +30 |
| Sustained deterioration | +20 |
| Relevant active alarm | +25 |
| Recent threshold breach | +25 |

Its alert threshold, selected on validation data, is **45**.

This gives us a practical comparison:

> Does the trained model provide useful detection beyond a simple, transparent
> set of rules?

The model is **not trained to reproduce this score**. It learns from future
degradation labels.

The heuristic components explain only the heuristic. They are **not an
explanation of how the Random Forest produced its score**.

## 11. What happens during your demo

At minute 150, EVC-01 has:

| Evidence | Value |
|---|---:|
| Latest latency | 66.10 ms |
| Packet loss | 0.294% |
| Active alarm severity | 0 |
| Complete historical intervals | 6/6 |
| Heuristic score | 20 |
| Model score | Approximately 0.99025 |
| Model band | High |

Current latency and loss are below the simulated degradation thresholds. The
heuristic identifies deterioration but remains below its alert threshold.

The Random Forest assigns High risk from the combined historical feature
pattern.

The replay's confirming bad intervals are:

```text
165-170: Bad
170-175: Bad
175:     Degradation confirmed
```

So the minute-150 forecast is:

- **15 minutes before the confirming bad intervals begin**.
- **25 minutes before confirmation**.

That future timeline comes from evaluation ground truth. It is not supplied to
the model when predicting at minute 150.

Meanwhile, EVC-12 has missing required telemetry and receives **insufficient
evidence with a null score**.

## 12. How Spring Boot and Python work together

The serving path is:

```text
GET replay request or POST observations
                 |
                 v
Spring Boot :8180
Validate request and call inference
                 |
                 v
FastAPI / Python :8181
Apply time filtering and evidence gates
                 |
                 v
Extract historical features
                 |
                 v
Run inference with the trained model
                 |
                 v
Service results and customer summaries
                 |
                 v
JSON response through Spring Boot
```

The replay endpoint recomputes predictions using bundled synthetic observations.

The normal POST endpoint evaluates the observations supplied in the request. It
does **not** silently fill gaps using replay data.

Spring Boot is the application-facing adapter; Python owns feature extraction
and model execution. There is no second predictive model inside Spring Boot.

## 13. How service predictions become customer results

The customer summary takes the **highest risk band among assessed requested
services**.

For example:

```text
Customer Org-B
  EVC-02: High
  EVC-03: High
  EVC-04: High

Customer summary: High
```

It also preserves counts of insufficient-evidence and already-degraded services.

This is an aggregation rule, not a separately trained customer model, and not a
mathematical probability that the customer will experience an outage.

Shared-resource exposure emerges because associated services receive evidence
from common resources, not because we manually add points for having more
customers.

## 14. What the evaluation tells us

On held-out synthetic test episodes:

| Metric | Random Forest | Heuristic |
|---|---:|---:|
| Precision | 54.2% | 31.3% |
| Recall | 82.6% | 67.7% |
| False-alert windows | 136 | 290 |

**Precision:** Of the model's alerting windows, about 54% had a new confirmation
within the forecast horizon.

**Recall:** Of the positive assessed windows, about 83% were flagged.

These are **window-level metrics**, not percentages of distinct incidents or
customers.

Forecast coverage was approximately **78.6%**, excluding already-degraded
windows. Median proactive lead was **15 minutes among proactively warned service
events**.

One important qualification: service-episodes containing any false alert were
**46 for the model versus 44 for the heuristic**. Therefore, fewer false-alert
windows do not establish fewer operational escalations.

## Bottom line

**We have demonstrated a complete technical pipeline: inventory relationships
-> historical evidence -> trained early-warning model -> service risk ->
customer prioritization, with explicit uncertainty.**

What remains unproven is production effectiveness. That requires aligned real
observations and incident labels, temporal backtesting, validation of resource
exposure, and controlled shadow operation before making outage-prevention or
savings claims.

## Implementation references

- `impact_predictor/features.py`: Historical features, evidence gates and heuristic.
- `impact_predictor/training.py`: Model fitting, episode splits and threshold selection.
- `impact_predictor/inference.py`: Model scoring, risk bands and evidence output.
- `models/run-001/evaluation.json`: Recorded evaluation results.
- `END_TO_END_EXPLANATION.md`: Full data-to-deployment technical explanation.
- `HACKATHON_DEMO_RUNBOOK.md`: Commands and narration for the demonstration.
