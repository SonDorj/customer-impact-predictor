<!-- AIFEL-AI-LABEL-V1: product="AIFEL Team Assistant"; origin=ai_generated -->
# Customer Impact Predictor: End-to-End Explanation

[AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]

## Overview

The system predicts risk at the service level, then uses inventory relationships
to identify the associated customers.

The most important distinction is:

| Component | What we actually used |
|---|---|
| Customer/service/resource relationships | Supplied Ethernet inventory, cleaned and reduced to a demonstration neighborhood |
| Performance measurements | Synthetic |
| Alarm events | Synthetic |
| Maintenance schedules | Synthetic |
| Future degradation labels | Synthetic |
| Predictor | A genuinely trained Random Forest |
| Evaluation results | Held-out synthetic results, not production accuracy |

We have built a functioning prediction pipeline, **not yet a production-validated
forecasting system**.

The complete flow is:

```text
Supplied inventory files
        |
        v
Validate, clean and join inventory
        |
        v
Qualified Ethernet cohort
        |
        v
Select a meaningful shared-resource neighborhood
        |
        v
Replace identifiers with presentation aliases
        |
        v
Simulate resource conditions over time
        |
        +--------------------------+
        |                          |
        v                          v
Historical observations      Future degradation outcomes
        |                          |
        v                          v
Evidence gates + features     Training labels
        |                          |
        +------------+-------------+
                     |
                     v
            Train Random Forest
                     |
                     v
          Validate thresholds and test
                     |
                     v
             Save trained artifact
                     |
                     v
      Spring Boot -> FastAPI -> prediction
                     |
                     v
       Service risk -> customer rollup
```

## Contents

1. [Cleaning the supplied inventory](#1-cleaning-the-supplied-inventory)
2. [Selecting the demonstration neighborhood](#2-selecting-the-demonstration-neighborhood)
3. [Why we generated synthetic signals](#3-why-we-generated-synthetic-signals)
4. [How synthetic episodes are generated](#4-how-synthetic-episodes-are-generated)
5. [Defining the prediction target](#5-defining-the-prediction-target)
6. [Turning resource observations into service evidence](#6-turning-resource-observations-into-service-evidence)
7. [Evidence gates](#7-evidence-gates)
8. [The 19 model features](#8-the-19-model-features)
9. [Constructing training examples](#9-constructing-training-examples)
10. [Training, validation and testing](#10-training-validation-and-testing)
11. [Choosing thresholds and risk bands](#11-choosing-thresholds-and-risk-bands)
12. [The separate heuristic comparator](#12-the-separate-heuristic-comparator)
13. [Interpreting the evaluation](#13-interpreting-the-evaluation)
14. [Saving and loading the model](#14-saving-and-loading-the-model)
15. [Processing prediction requests](#15-processing-prediction-requests)
16. [A real example from the bundled model](#16-a-real-example-from-the-bundled-model)
17. [Converting service predictions into customer impact](#17-converting-service-predictions-into-customer-impact)
18. [Spring Boot and FastAPI responsibilities](#18-spring-boot-and-fastapi-responsibilities)
19. [Implemented scope and remaining limitations](#19-implemented-scope-and-remaining-limitations)
20. [Implementation reference](#20-implementation-reference)

## 1. Cleaning the supplied inventory

### 1.1 What we needed from inventory

Before predicting anything, we needed a reliable answer to:

> If resource R deteriorates, which services are associated with it, and which
> customers own those services?

Our selected relationship is:

```text
Customer / BusOrg
        |
        v
Ethernet EVC service
        |
        +------------------+
        |                  |
        v                  v
Endpoint A UNI        Endpoint Z UNI
        |                  |
        v                  v
Access resource       Access resource
PE resource           PE resource
```

An EVC is the logical service. A UNI represents the customer-facing attachment.
The resource associations connect those attachments to network equipment and
interfaces.

**These are inventory-declared associations, not a verified end-to-end forwarding
path.**

### 1.2 Which files contributed

Although we collected 15 supplied datasets, we did not force every file into the
predictor.

| Input | Purpose |
|---|---|
| `EVCs 1.csv` | EVC identifiers, BusOrg, bandwidth and both endpoint UNI identifiers |
| `WhitelistedPorts.csv` | UNI ownership, status, access device/port and PE device/port |
| `CustomerPorts.csv` | Optional corroboration of UNI customer BAN and lifecycle status |
| Local EVC workbook | Reconciliation against the canonical EVC CSV |
| Local inventory-quality CSV | Historical provisioning-exception flags only |

Other product datasets, location files and archives were preserved but not joined
into this Ethernet cohort.

That kept the first POC focused on relationships we could demonstrate rather than
speculative cross-product joins.

### 1.3 Basic structural validation

The cleaning script checks that:

- Required columns exist.
- Ordinary CSV inputs do not have duplicate headers.
- Rows are structurally valid.
- Identifier groups can be resolved consistently.
- Source checksums match the recorded originals.

Malformed input is not silently accepted.

One inventory-quality file had repeated exception-column names. That file
received special positional handling: we extracted only whether a historical
exception existed, not the exception free text.

**A provisioning exception was never treated as an outage label.**

### 1.4 Identifier normalization

For inventory joins, we trim surrounding whitespace but preserve identifier
meaning.

```text
"  ABC-001  " -> "ABC-001"
"000123"     -> "000123"
"Port-A"     remains distinct from "port-a"
```

We do not indiscriminately lowercase identifiers, remove punctuation or convert
them into integers. Those transformations could accidentally merge different
resources or destroy leading zeros.

Lifecycle values such as `ACTIVE` are handled case-insensitively because they are
status values rather than identity keys.

### 1.5 Duplicate handling

Rows are grouped by their identifiers.

| Situation | Handling |
|---|---|
| Identical duplicate records | Collapse into one |
| Same identifier with conflicting records | Exclude the ambiguous identifier |
| Missing identifier | Record an issue rather than inventing one |

We do not arbitrarily select one conflicting mapping and pretend it is
authoritative.

### 1.6 Service qualification rules

An EVC enters the clean cohort only when:

1. Its identifier and BusOrg are present and unambiguous.
2. Both endpoint UNI identifiers exist.
3. The two endpoint UNIs differ.
4. Both UNIs resolve in `WhitelistedPorts.csv`.
5. Both have complete access-device/access-port and PE-device/PE-port mappings.
6. The EVC BusOrg matches both UNI BusOrgs.
7. Both UNI statuses are active.
8. Any available `CustomerPorts.csv` corroboration does not contradict the
   customer BAN or active lifecycle status.

Absence from `CustomerPorts.csv` alone does not reject a service; that file is
corroboration, not universal membership.

We keep these separate:

```text
EVC billing account
UNI billing account
UNI customer BAN
```

They are not assumed to be interchangeable customer identifiers.

### 1.7 Cleaning result

| Item | Count |
|---|---:|
| Original EVC rows | 9,646 |
| Distinct EVC identifier groups | 9,645 |
| Accepted EVC services | **2,595** |
| Excluded EVC groups | 7,050 |
| BusOrgs | **368** |
| UNIs | **1,756** |
| Resources | **1,957** |
| Endpoint rows | **5,190** |
| Deduplicated resource-service relationships | **9,610** |
| Resources shared across BusOrgs | 116 |

The 5,190 endpoint rows are:

```text
2,595 services x 2 endpoints
```

They are **not 5,190 separate services**.

An excluded service can fail several rules, so exclusion-reason counts overlap.

### 1.8 What a resource means here

A resource is identified by the source-scoped tuple:

```text
(resource role, exact device name, exact port name)
```

For example:

```text
(access, device-X, port-Y)
```

is distinct from:

```text
(PE, device-X, port-Y)
```

A resource is not automatically an entire router. A future device-wide alarm
adapter would need to map that device event to all relevant interface resources.

The customer grouping is one alias per BusOrg. It is not a verified ultimate-parent
customer hierarchy.

### 1.9 Clean output tables

| Output | Meaning |
|---|---|
| `customers.csv` | One customer alias per BusOrg |
| `services.csv` | One row per accepted EVC |
| `unis.csv` | UNI ownership and resource associations |
| `resources.csv` | Distinct role/device/port resources |
| `service_endpoints.csv` | Both endpoint relationships |
| `resource_service_map.csv` | Deduplicated resource-to-service exposure |
| `inventory_cohort.csv` | Convenient flattened endpoint view |
| `excluded_services.csv` | Rejected identifiers and reasons |
| `quality_report.json` | Counts, qualification rules and limitations |
| `provenance.json` | Source/output checksums and traceability |

The preparation implementation is in the separate local
`inventory-tools/build_cohort.py`. The portable application repository starts with
the already-prepared alias-only inventory.

## 2. Selecting the demonstration neighborhood

We did not randomly pick 12 services. A random sample might contain no shared
resources and therefore fail to demonstrate customer-impact correlation.

| Slice | Composition |
|---|---|
| Primary neighborhood | Five services sharing `R-01`, across three organizations |
| Secondary neighborhood | Three services sharing `R-02`, across two other organizations |
| Controls | Three services separated from those event resources |
| Missing-evidence case | One additional service with complete inventory but withheld replay telemetry |

The resulting neighborhood has:

```text
12 EVC services
9 organization aliases
19 UNIs
31 resources
24 endpoint rows
```

The selection preserves both endpoints and the full qualified-cohort fan-out of
the two selected event resources.

"Full" here means within our qualified inventory cohort, not proof that every
associated production service across Lumen has been discovered.

The controls and missing-evidence service were selected with resource separation.
This prevents a supposedly independent control from receiving the same simulated
resource exposure accidentally.

### Alias handling

Presentation identifiers look like:

```text
EVC-01
UNI-01
R-01
Org-A
```

The private source-to-alias crosswalk is not distributed in the Git package.

Aliases do not make company-derived relationships unrestricted public data.
The package still belongs in an approved private/internal repository.

## 3. Why we generated synthetic signals

Our bounded source discovery did not establish a usable, aligned historical
training dataset:

| Source | Limitation in the inspected data |
|---|---|
| RFM | Selected retrievals returned empty alert data |
| HiPer | Selected measurements were missing/null and did not establish cohort alignment |
| Clarify/GCR | Inspected records did not establish usable service-linked incident labels for the cohort |

That does not prove useful production data does not exist. It means we did not
have a sufficiently verified dataset for this hackathon model.

> We retained the supplied inventory relationships and simulated the observations
> and future outcomes.

We did **not** create labels by applying our heuristic score and then train a
model to reproduce that same score. That would mostly teach the model our own
rule.

## 4. How synthetic episodes are generated

Implementation: `impact_predictor/simulation.py`.

### 4.1 Episode structure

We generate **300 independent episodes**.

```text
Duration:               6 hours
Measurement interval:   5 minutes
Intervals per resource: 72
Services:               Same 12-service neighborhood
```

An episode is a simulated run of the neighborhood, not an actual production
incident.

Each run varies conditions such as the stressed resource, deterioration start,
strength, ramp speed, measurement noise, observation delays, missing observations,
alarm transitions and feed availability.

The original run uses seed `2026` for reproducibility.

### 4.2 Six scenario families

| Scenario | What it represents |
|---|---|
| Healthy variation | Normal fluctuations without a deliberate deterioration profile |
| Gradual deterioration | A resource condition worsens over time |
| Intermittent fault | Repeated fault-like bursts |
| Planned maintenance with expected events | Scheduled work with modeled resource activity |
| Unexpected deterioration during maintenance | Scheduled work does not guarantee harmless behavior |
| Missing or stale evidence | Required observations are unavailable |

Scenario names are bookkeeping. They are **not model features**.

### 4.3 The hidden resource-condition process

Each resource has an internal simulated stress value.

```text
new stress =
    persistence x previous stress
  + response to the scenario's desired stress
  + random variation
```

That stress drives several related outputs:

```text
Resource stress
    |
    +--> Latency
    +--> Packet loss
    +--> Jitter
    +--> Alarm severity
```

The simulator uses relationships of the form:

```text
Underlying latency ~= resource baseline + 75 x stress

Underlying loss ~= 0.02 + 1.1 x max(0, stress - 0.35)
```

The loss is capped at 100%. Measured observations then receive additional noise.

This produces correlated signals: worsening conditions can produce rising
latency, loss, jitter and alarms.

**The model never receives the hidden stress value itself.**

### 4.4 Imperfect observations

| Imperfection | Current configuration |
|---|---|
| Independent performance dropout | 1.5% |
| Performance observation delay | 0, 5 or 10 minutes |
| Delay probabilities | 85%, 12%, 3% |
| Latency measurement noise | Standard deviation 2.5 ms |
| Packet-loss measurement noise | Standard deviation 0.03 percentage points |
| Alarm-feed unavailability | Simulated per interval |
| Maintenance-feed unavailability | Simulated per interval |

There are two important clocks:

```text
eventMinute       When the measurement/event occurred
observedMinute    When the predictor could know about it
```

A measurement from minute 145 that arrives at minute 155 cannot influence a
prediction made at minute 150.

### 4.5 Source-inspired tables

| Table | Contents |
|---|---|
| `hiper_performance.csv` | Resource latency, delivery percentage and jitter |
| `rfm_alarms.csv` | Resource alarm raises/clears and severity |
| `clarify_gcr_maintenance.csv` | Maintenance windows and when they became known |
| `feed_status.csv` | Whether optional event feeds are available |
| `clarify_incident_outcomes.csv` | Future service-degradation confirmation times |
| `episode_index.csv` | Episode identity, scenario and split |
| `feature_windows.csv` | Features, assessment status and training target |

These are **source-inspired normalized schemas**, not claimed replicas of native
RFM, NVD/HiPer or Clarify API payloads.

## 5. Defining the prediction target

At time `t`, the target is:

> Will this service develop a new confirmed degradation in the next 30 minutes?

```text
Target = 1 if a new confirmation occurs in (t, t + 30 minutes]
Target = 0 otherwise
```

The interval excludes a confirmation occurring exactly at `t`: that is not a
future onset.

### 5.1 What counts as a bad interval?

A modeled service interval is bad when an attached resource has:

```text
Latency >= 100 ms
OR
Packet loss >= 1%
```

Jitter is an input feature, but not a direct outcome threshold.

### 5.2 Why require confirmation?

One abnormal sample can be transient. We require:

```text
Two consecutive bad five-minute intervals
```

Confirmation is recorded at the end of the second bad interval.

```text
165---------170---------175
   Bad interval   Bad interval
                         |
                         v
                Confirmed at 175
```

This distinguishes the beginning of impairment, the first completed bad
measurement and the later confirmation. They are different times, particularly
when discussing lead time.

### 5.3 Where labels come from

Labels are generated from the simulator's underlying resource conditions and
future confirmation timeline.

They are **not** generated from the heuristic score, model prediction, scenario
names passed into the classifier or historical provisioning exceptions.

Observed measurements can be noisy or delayed while the simulator retains an
underlying outcome timeline. This separates observed evidence from future ground
truth.

## 6. Turning resource observations into service evidence

Implementation: `impact_predictor/features.py`.

For each service, we retrieve its inventory-linked resources. The actual
`EVC-01` resource set is:

```text
R-01
R-09
R-10
R-11
```

At each historical timestamp, service-level measurements are constructed as:

```text
Service latency = maximum attached-resource latency
Service loss    = maximum attached-resource packet loss
Service jitter  = maximum attached-resource jitter
```

This is a deliberately conservative **worst-attached-resource proxy**.

It assumes an unprotected simulated service. It does not model actual routing,
redundant paths, failover or protection switching.

If several services share `R-01`, that resource's observations contribute to each
associated service.

This is why the predictor is topology-aware even though the classifier is not a
graph neural network.

**Inventory determines the evidence each service receives.**

## 7. Evidence gates

Before invoking the classifier, the system decides whether it has sufficient
evidence.

### 7.1 Historical window

At prediction time `t`, it considers six completed five-minute intervals:

```text
(t - 30 minutes, t]
```

At minute 150, these are measurements ending at:

```text
125, 130, 135, 140, 145, 150
```

Only observations already received by minute 150 are eligible.

For repeated observations of the same resource/timestamp, the latest version
received by the prediction time is used.

### 7.2 Complete service intervals

An interval is usable only when **every attached resource** has a valid
observation at that timestamp.

This is stricter than checking each resource independently. If different resources
are missing at different times, their individually acceptable histories might
still leave too few complete service intervals.

Valid performance requires finite values, nonnegative latency/jitter and packet
delivery between 0 and 100.

### 7.3 Minimum coverage and freshness

```text
At least 5 complete intervals out of the last 6
Newest complete interval no more than 10 minutes old
```

Otherwise:

```json
{
  "status": "insufficient_evidence",
  "riskBand": "Insufficient evidence",
  "uncalibratedModelScore": null
}
```

We do not replace missing required telemetry with healthy measurements.

### 7.4 Already-degraded services

If the last two current observed intervals are bad:

```text
status = already_degraded
model score = null
```

The system does not present an existing degradation as a new future prediction.

### 7.5 Missing optional feeds

Alarm and maintenance feeds are optional.

```text
Alarm/maintenance measurements -> missing values
Availability flags            -> false
```

That is different from:

```text
Feed working, no active alarms
```

A working feed with zero alarms is evidence. A failed feed is missing evidence.

## 8. The 19 model features

The historical window becomes one numeric feature vector per service and
prediction time.

| Group | Features |
|---|---|
| Latency | Latest, mean, maximum, standard deviation, slope |
| Packet loss | Latest, mean, maximum, slope |
| Jitter | Latest value |
| Persistence | Number of recent threshold-breaching intervals |
| Alarms | Maximum active severity, raises in the last 30 minutes, feed-available flag |
| Maintenance | Active schedule, schedule starting within the next 30 minutes, feed-available flag |
| Evidence quality | Valid-history fraction, age of newest complete service observation |

```text
5 + 4 + 1 + 1 + 3 + 3 + 2 = 19
```

The exact feature names, in model input order, are:

```text
latency_latest_ms
latency_mean_ms
latency_max_ms
latency_std_ms
latency_slope_per_interval_ms
loss_latest_pct
loss_mean_pct
loss_max_pct
loss_slope_per_interval_pct
jitter_latest_ms
recent_breach_count
active_alarm_max_severity
alarm_raises_last_30m
alarm_feed_available
maintenance_active
maintenance_starting_next_30m
maintenance_feed_available
valid_history_fraction
newest_service_age_minutes
```

Slopes are measured per five-minute interval. Packet loss is expressed in
percentage points:

```text
Packet delivery 99.7% -> packet loss 0.3%
```

Maintenance is eligible only if it was known and observed by prediction time.
A future scheduled start can therefore be a valid feature without leaking the
future.

The current classifier does **not** receive customer IDs, service IDs, scenario
names, future incident times, customer revenue or business criticality.

Shared-resource fan-out is reflected through inventory-based evidence
propagation, not a separate numeric fan-out feature.

## 9. Constructing training examples

One training row represents:

```text
One service
At one prediction time
Within one episode
```

The following rows illustrate the structure; these are not quoted dataset rows:

```text
Episode | Service | Time | Historical features | Future target
EP-0001 | EVC-01  | 150  | ...19 values...      | 1
EP-0001 | EVC-02  | 150  | ...19 values...      | 0
EP-0001 | EVC-01  | 155  | ...19 values...      | 1
```

The identifiers organize rows but are excluded from the feature matrix.

### Prediction times

Training predictions run from minute 30 through minute 330, every five minutes.
That provides:

```text
61 prediction times per service
```

The start allows a complete historical window. The end leaves 30 minutes of known
future outcomes before the six-hour episode finishes.

We do not label an example using a future window extending beyond the available
episode.

```text
300 episodes x 12 services x 61 times
= 219,600 service-windows
```

Not all candidates become classifier inputs. Missing-evidence and
already-degraded windows are recorded separately.

## 10. Training, validation and testing

Implementation: `impact_predictor/training.py`.

### 10.1 Split whole episodes, not adjacent rows

| Split | Episodes | Assessed classifier rows |
|---|---:|---:|
| Training | 210 | **119,540** |
| Validation | 45 | **25,883** |
| Test | 45 | **25,821** |

All services and timestamps from an episode remain together.

```text
Bad split:
Minute 150 of an incident -> training
Minute 155 of the same incident -> testing
```

Those rows are highly related. Such a split could make the evaluation look
stronger than it is. Whole-episode separation reduces that problem.

However, **all splits still share the same inventory topology and generator
family**. We have not demonstrated generalization to an unseen network.

### 10.2 Missing-value preprocessing

The fitted pipeline is:

```text
SimpleImputer
      |
      v
RandomForestClassifier
```

The imputer learns medians from training rows only, replaces missing optional
numeric features and adds indicators showing which features were missing.

In the actual bundled model, the 19 original features become **23 transformed
inputs** after missing indicators are added.

This does not bypass the required-performance gate. Missing required performance
already caused abstention before this stage.

### 10.3 Random Forest configuration

| Parameter | Value |
|---|---:|
| Trees | 120 |
| Maximum depth | 10 |
| Minimum samples per leaf | 20 |
| Bootstrap sample size | 80% of training-row count |
| Class weighting | `balanced_subsample` |
| Worker threads | 2 |
| Seed | 2026 |

Each tree learns splits from historical features and future outcome labels.

The bootstrap sample uses replacement; "80%" does not mean 80% distinct rows.

Depth and minimum-leaf constraints reduce the tendency to memorize small
collections of examples.

Class weighting matters because future-degradation windows are rare.

### 10.4 What the forest produces

For a new feature vector:

```text
Tree 1 -> estimated positive-class score
Tree 2 -> estimated positive-class score
...
Tree 120 -> estimated positive-class score
                 |
                 v
             Average
```

More precisely, scikit-learn averages the trees' leaf class-probability estimates.
That output is exposed as:

```text
uncalibratedModelScore
```

It is not a validated production outage probability.

### 10.5 What this particular forest learned to use

The largest global impurity-based importances in the bundled model include:

| Feature | Approximate importance |
|---|---:|
| Latency standard deviation | 17.7% |
| Maximum latency | 15.4% |
| Mean latency | 12.6% |
| Latest jitter | 9.3% |
| Latest latency | 8.0% |
| Maximum packet loss | 7.9% |

These describe the fitted forest globally within this simulation.

They are **not causal effects or explanations for one particular prediction**.

## 11. Choosing thresholds and risk bands

We do not arbitrarily use `0.5` as the alert threshold.

### High threshold

On validation data, we evaluate precision and recall across score thresholds and
select the threshold maximizing:

```text
F1 = 2 x precision x recall / (precision + recall)
```

If multiple thresholds tie, the higher threshold is preferred.

The test set is not used to select the threshold.

### Lower bands

Among distinct validation scores below High:

```text
Watch threshold    = 50th percentile
Elevated threshold = 90th percentile
```

The bundled thresholds are:

| Band | Score range |
|---|---|
| Low | Below 0.06757793356275152 |
| Watch | At least 0.06757793356275152 and below 0.11913129621612946 |
| Elevated | At least 0.11913129621612946 and below 0.8125858475756745 |
| High | At least 0.8125858475756745 |

These lower bands are descriptive score bands, not independently validated
operational severity classes.

## 12. The separate heuristic comparator

| Evidence | Points |
|---|---:|
| Latest latency >=80 ms or loss >=0.7% | +30 |
| Latency slope >=3 ms/interval or loss slope >=0.06 percentage points/interval | +20 |
| Active alarm severity >=2 | +25 |
| At least one recent threshold breach | +25 |

Maximum:

```text
100 points
```

Its alert threshold, selected separately using validation data, is **45**.

The implemented heuristic is simpler than some early discussion examples. It does
not currently add a shared-resource-exposure bonus or automatically subtract
maintenance points.

> The heuristic does not determine the Random Forest score, and its component
> breakdown is not an explanation of the forest.

They are parallel approaches evaluated against the same future labels.

## 13. Interpreting the evaluation

The actual synthetic test results are:

| Metric | Random Forest | Heuristic |
|---|---:|---:|
| Precision | **54.21%** | 31.28% |
| Recall | **82.56%** | 67.69% |
| Average precision | **0.6772** | 0.2503 |
| False-alert windows | **136** | 290 |
| Service-episodes with any false alert | 46 | **44** |
| Service-degradation events warned before confirmation | 41/46 | 41/46 |
| Events warned before the confirming bad intervals began | **39/46** | 35/46 |

For the Random Forest's High-alert decision:

```text
True-positive windows:   161
False-positive windows:  136
Missed positive windows: 34
```

```text
Precision = 161 / (161 + 136) = 54.21%
Recall    = 161 / 195         = 82.56%
```

These are service-window measurements, not counts of independent network
incidents. One underlying resource event can affect multiple services.

### Why we do not emphasize accuracy

Only about 0.76% of assessed test windows are positive.

A model that always predicted "no future degradation" would achieve about
**99.24% accuracy** while detecting none of them.

Precision, recall, average precision, coverage and lead time are more informative.

### Coverage and lead time

```text
25,821 assessed windows
7,038 insufficient-evidence windows
81 already-degraded windows
```

Forecast coverage, excluding already-degraded windows, is approximately
**78.58%**:

```text
25,821 / (25,821 + 7,038)
```

Median proactive lead time among proactively warned events is **15 minutes**.
That does not mean every service event received 15 minutes of warning.

Although false-alert windows decreased, service-episodes with any false alert did
not. We cannot claim proven fewer operational escalations from these results.

We also cannot claim measured financial savings, prevented production outages or
real-world predictive accuracy.

## 14. Saving and loading the model

After training, we save:

```text
model.joblib
evaluation.json
data_dictionary.json
heldout_predictions.csv
training manifests
separate demonstration replay
```

The model bundle includes the fitted imputer and Random Forest, feature order,
risk-band thresholds, heuristic alert threshold, synthetic-domain designation,
and contract/inventory provenance hashes.

The training process reloads the newly saved model and checks prediction
consistency.

At serving startup, the application checks:

```text
Inventory checksums
Contract checksum
Core feature/inference code checksums
Model and replay checksums
Scientific dependency versions
Feature schema and synthetic-domain metadata
```

This helps prevent accidentally serving the wrong model with incompatible
features.

Checksums provide integrity checks, not independent proof that an arbitrary
downloaded model is trustworthy. Joblib/pickle artifacts must come from a trusted
source.

The historical bundled artifact is in `models/run-001/`. Newly generated
experiments go into ignored `runs/` directories.

The portable package retains original training provenance while separately
verifying its alias-only inventory. Historical references to excluded private
inputs are metadata, not runtime dependencies.

## 15. Processing prediction requests

There are two distinct paths.

### Demonstration replay

```http
GET /api/v1/demo/predictions?minute=150
```

This reads the packaged synthetic observations and recomputes predictions as of
minute 150.

It does not merely return hardcoded High/Low labels from a snapshot.

The replay is a separate scripted episode, not part of fitting or threshold
selection. Its representative frame was selected for presentation; scores were
not edited.

### Provided observations

```http
POST /api/v1/impact/predictions
```

This uses observations from the request. It does not silently fill missing
request telemetry from the replay.

```text
Validate request
      |
      v
Resolve requested services and resources
      |
      v
Filter observations as of prediction time
      |
      v
Build complete service-level historical intervals
      |
      v
Apply evidence/current-degradation gates
      |
      v
Construct 19 features
      |
      v
Apply fitted imputer
      |
      v
Run fitted Random Forest
      |
      v
Apply frozen risk-band thresholds
      |
      v
Compute separate heuristic and evidence summary
      |
      v
Aggregate assessed service bands by customer
```

No retraining happens during prediction.

The observation arrays are:

| Array | Fields |
|---|---|
| `performance` | `resourceId`, `eventMinute`, `observedMinute`, `latencyMs`, `packetDeliveryPct`, `jitterMs` |
| `alarms` | `resourceId`, `eventMinute`, `observedMinute`, `severity`, `action` |
| `maintenance` | `resourceId`, `startMinute`, `endMinute`, `knownMinute`, `observedMinute` |
| `feedStatus` | `eventMinute`, `observedMinute`, `alarmFeedAvailable`, `maintenanceFeedAvailable` |

Minute values are relative to the simulated episode, not live production
wall-clock timestamps. The packaged representative replay has no maintenance
records; maintenance context is supported in training and POST requests.

## 16. A real example from the bundled model

The following values were recomputed from the packaged artifact at replay
minute 150.

For `EVC-01`:

| Evidence | Actual value |
|---|---:|
| Latest service latency | **66.10 ms** |
| Mean latency over the window | 42.43 ms |
| Latency standard deviation | 13.51 ms |
| Latency slope | **7.60 ms per five-minute interval** |
| Latest packet loss | **0.294%** |
| Complete historical intervals | **6/6** |
| Active alarm maximum severity | **0** |
| Maintenance active | No |
| Heuristic score | **20/100** |
| Random Forest score | **0.99025** |
| Model band | **High** |

This is a useful demonstration because:

```text
Latency has not reached 100 ms.
Loss has not reached 1%.
There is no active alarm.
The heuristic is below its alert threshold.
The learned model nevertheless produces High.
```

The forest is responding to the historical feature pattern, rather than waiting
for the current degradation threshold.

In the simulator's future outcome timeline, the service's next confirmation
occurs at **minute 175**.

The confirming bad intervals cover:

```text
165-170
170-175
```

The prediction at minute 150 is:

```text
25 minutes before confirmation
15 minutes before that confirming bad-interval pair begins
```

That future timeline is available for evaluating the demonstration.
**It is not supplied to the inference function.**

The score of `0.99025` must not be presented as a 99.025% real-world outage
probability.

Other actual results at that frame include:

| Service | Result |
|---|---|
| EVC-01 through EVC-05 | High |
| EVC-06 through EVC-08 | Elevated |
| EVC-09 control | Low |
| EVC-10 control | Elevated |
| EVC-11 control | Watch |
| EVC-12 | Insufficient evidence; null score |

The controls are not all Low. We retain those results rather than manipulating
them to improve the demo.

## 17. Converting service predictions into customer impact

The model is trained to forecast **service degradation**, not customer
dissatisfaction, churn or revenue loss.

After prediction, inventory maps services to organization aliases.

```text
Org-B
  |
  +-- EVC-02 -> High
  +-- EVC-03 -> High
  +-- EVC-04 -> High
```

The customer summary becomes:

```text
Highest assessed-service band:  High
Assessed services:              3
Insufficient-evidence services: 0
Already-degraded services:      0
```

The rollup preserves counts of assessed, unassessed and already-degraded
services.

An organization with no assessed services does not receive a fabricated Low band.
If current degradation exists, that operational status is retained.

When only a subset of services is requested, aggregation covers the returned
subset, not every service the organization might own.

This is a deterministic aggregation, not a second customer-level
machine-learning model.

## 18. Spring Boot and FastAPI responsibilities

### Spring Boot

Spring Boot is the application-facing REST layer on port `8180`.

It provides typed contracts, request validation, dependency health and HTTP error
mapping. Its `RestClient` calls the Python inference service.

It does not implement a second copy of the model.

### FastAPI

FastAPI runs on port `8181`.

It owns trusted model loading, inventory access, replay loading, as-of-time
filtering, feature extraction, evidence gates, model inference and customer
aggregation.

The fitted model is loaded at startup and reused across requests.

If inference is unavailable, Spring returns an explicit failure rather than a
healthy-looking prediction.

| Situation | Spring response |
|---|---:|
| Invalid observation request | 400 |
| Unknown service | 404 |
| Malformed inference response | 502 |
| Inference unavailable | 503 |
| Inference timeout | 504 |

Direct FastAPI observation-schema errors use HTTP `422`.

### Endpoint mapping

| Spring endpoint | Python endpoint |
|---|---|
| `GET /actuator/health` | `GET /health` |
| `GET /api/v1/model` | `GET /v1/model` |
| `GET /api/v1/inventory` | `GET /v1/inventory` |
| `GET /api/v1/demo/predictions?minute=150` | `GET /v1/demo/predictions?minute=150` |
| `POST /api/v1/impact/predictions` | `POST /v1/predictions` |

Both services listen on loopback by default. These are unauthenticated POC
services and should not be exposed publicly.

## 19. Implemented scope and remaining limitations

| Implemented now | Not established yet |
|---|---|
| Deterministic inventory cleaning and correlation | Continuously refreshed production inventory |
| Preserved EVC endpoints and resource associations | Verified forwarding paths and protection behavior |
| Synthetic performance, alarms, maintenance and outcomes | Aligned historical production training data |
| Trained Random Forest and heuristic comparator | Calibrated production outage probabilities |
| Explicit missing-evidence abstention | Production-wide inventory-staleness detection |
| Episode-held-out synthetic evaluation | Unseen-network and real-world temporal validation |
| FastAPI and Spring Boot prediction services | Live production source adapters and continuous ingestion |
| Customer rollups from service forecasts | Revenue, criticality or churn prediction |
| Maintenance context | A separate integrated change/deployment feed |
| JSON APIs and Python Swagger documentation | A dedicated front-end UI |
| Prediction responses | Automated ticket creation or remediation |

There is **no LLM or generative-AI model in the prediction path**.

The predictive AI is the trained tabular Random Forest. Inventory correlation and
evidence gates make its output operationally interpretable without pretending
that missing data means health.

## 20. Implementation reference

Paths below the portable repository root are relative to
`customer-impact-predictor/`. The private inventory-preparation tools remain in
the separate local `inventory-tools/` folder.

| Responsibility | Implementation or artifact |
|---|---|
| Original inventory cleaning | Separate `inventory-tools/build_cohort.py` |
| Neighborhood selection and aliasing | Separate `inventory-tools/build_demo_neighborhood.py` |
| Packaged alias-only inventory | `data/inventory/` |
| Approved target and simulation settings | `approved_contract.json` |
| Resource simulation and future outcomes | `impact_predictor/simulation.py` |
| Historical features, gates and heuristic | `impact_predictor/features.py` |
| Grouped fitting, thresholds and evaluation | `impact_predictor/training.py` |
| Dataset generation and training orchestration | `impact_predictor/__main__.py` |
| Individual assessment prediction | `impact_predictor/inference.py` |
| Portable paths and provenance checks | `impact_predictor/paths.py` |
| Python request/response schemas | `impact_predictor/api_models.py` |
| Python API, replay and customer aggregation | `impact_predictor/api.py` |
| Java application and REST adapter | `springboot-service/src/main/java/com/lumen/hackathon/impact/` |
| Trusted trained bundle and metrics | `models/run-001/` |
| Python regression and integration checks | `tests/` |
| Setup, startup and demonstration commands | `README.md` |
