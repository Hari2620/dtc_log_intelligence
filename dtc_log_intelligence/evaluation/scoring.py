"""Grades diagnoses against the generator's ground truth. This is only
possible because the data is synthetic and the labels are closed-set --
the honest justification for building a generator instead of sourcing real
fault logs (see README).

An unparseable diagnosis counts as wrong, not excluded -- silently dropping
failed-to-parse cases from the denominator would flatter the accuracy number
in exactly the case (a provider that can't reliably return JSON) an eval is
supposed to catch.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from dtc_log_intelligence.diagnosis.diagnose import Diagnosis


@dataclass
class EvalReport:
    total: int
    correct: int
    per_class_total: dict[str, int]
    per_class_correct: dict[str, int]
    confusion: dict[str, dict[str, int]]  # confusion[true_class][predicted_class] = count
    misses: list[dict] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def per_class_accuracy(self) -> dict[str, float]:
        return {
            cls: (self.per_class_correct.get(cls, 0) / total if total else 0.0)
            for cls, total in self.per_class_total.items()
        }


def evaluate(ground_truth: dict[str, str], diagnoses: dict[str, Diagnosis]) -> EvalReport:
    per_class_total: dict[str, int] = defaultdict(int)
    per_class_correct: dict[str, int] = defaultdict(int)
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    misses: list[dict] = []
    correct = 0

    for session_id, true_class in ground_truth.items():
        diagnosis = diagnoses.get(session_id)
        predicted = diagnosis.root_cause if diagnosis else "no_diagnosis"

        per_class_total[true_class] += 1
        confusion[true_class][predicted] += 1

        is_correct = predicted == true_class
        if is_correct:
            correct += 1
            per_class_correct[true_class] += 1
        else:
            misses.append({
                "session_id": session_id,
                "true_class": true_class,
                "predicted": predicted,
                "reasoning": diagnosis.reasoning if diagnosis else "",
            })

    return EvalReport(
        total=len(ground_truth),
        correct=correct,
        per_class_total=dict(per_class_total),
        per_class_correct=dict(per_class_correct),
        confusion={k: dict(v) for k, v in confusion.items()},
        misses=misses,
    )
