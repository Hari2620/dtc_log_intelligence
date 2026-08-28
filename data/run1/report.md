# DTC Log Intelligence -- Evaluation Report

Provider: `mock` | Sessions: 80 | Overall accuracy: **97.5%** (78/80)

## Per-class accuracy

| Fault class | Sessions | Correct | Accuracy |
|---|---|---|---|
| cooling_failure | 20 | 20 | 100.0% |
| healthy | 18 | 18 | 100.0% |
| misfire_cascade | 15 | 15 | 100.0% |
| network_dropout | 15 | 15 | 100.0% |
| sensor_drift | 12 | 10 | 83.3% |

## Confusion matrix (rows = true class, columns = predicted)

| true \ predicted | cooling_failure | healthy | misfire_cascade | network_dropout | sensor_drift |
|---|---|---|---|---|---|
| cooling_failure | 20 | 0 | 0 | 0 | 0 |
| healthy | 0 | 18 | 0 | 0 | 0 |
| misfire_cascade | 0 | 0 | 15 | 0 | 0 |
| network_dropout | 0 | 0 | 0 | 15 | 0 |
| sensor_drift | 2 | 0 | 0 | 0 | 10 |

## Missed sessions

- `session_050`: true=**sensor_drift**, predicted=**cooling_failure** -- Naive lookup: first DTC code observed was P0128; mapped via a fixed code table with no trend or UDS context considered.
- `session_073`: true=**sensor_drift**, predicted=**cooling_failure** -- Naive lookup: first DTC code observed was P0128; mapped via a fixed code table with no trend or UDS context considered.
