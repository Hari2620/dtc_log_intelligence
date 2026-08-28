"""Renders an EvalReport as a markdown file -- the artifact you'd actually
paste into a PR description or an interview screen-share."""

from __future__ import annotations

from dtc_log_intelligence.evaluation.scoring import EvalReport


def render_markdown(report: EvalReport, provider_name: str, num_sessions: int) -> str:
    classes = sorted(report.per_class_total.keys())
    per_class_acc = report.per_class_accuracy()

    lines = [
        "# DTC Log Intelligence -- Evaluation Report",
        "",
        f"Provider: `{provider_name}` | Sessions: {num_sessions} | "
        f"Overall accuracy: **{report.accuracy:.1%}** ({report.correct}/{report.total})",
        "",
        "## Per-class accuracy",
        "",
        "| Fault class | Sessions | Correct | Accuracy |",
        "|---|---|---|---|",
    ]
    for cls in classes:
        total = report.per_class_total[cls]
        correct = report.per_class_correct.get(cls, 0)
        lines.append(f"| {cls} | {total} | {correct} | {per_class_acc[cls]:.1%} |")

    lines += ["", "## Confusion matrix (rows = true class, columns = predicted)", ""]
    predicted_labels = sorted({p for row in report.confusion.values() for p in row})
    header = "| true \\ predicted | " + " | ".join(predicted_labels) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(predicted_labels) + 1))
    for true_class in classes:
        row = report.confusion.get(true_class, {})
        cells = [str(row.get(p, 0)) for p in predicted_labels]
        lines.append(f"| {true_class} | " + " | ".join(cells) + " |")

    if report.misses:
        lines += ["", "## Missed sessions", ""]
        for miss in report.misses:
            lines.append(
                f"- `{miss['session_id']}`: true=**{miss['true_class']}**, "
                f"predicted=**{miss['predicted']}** -- {miss['reasoning']}"
            )

    return "\n".join(lines) + "\n"
