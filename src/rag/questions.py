"""Template questions for the company RAG CLI."""

from __future__ import annotations

TEMPLATE_QUESTIONS: dict[str, list[str]] = {
    "HR Policy (all roles)": [
        "What is the company's remote work policy?",
        "How many days of annual leave do employees receive?",
        "What is the probation period for new hires?",
        "What is the dress code policy?",
    ],
    "Workforce Analytics (employee role — aggregated)": [
        "How many employees work in the Data Engineering department?",
        "How many remote employees are based in Berlin?",
        "What seniority levels exist in the Security department?",
        "Which departments are in the Tech category?",
    ],
    "Workforce Analytics (hr_admin role only)": [
        "Who is the manager of employee ID 6?",
        "Which employees report to manager ID 2177?",
        "What promotions has employee ID 6 received?",
        "What salary band does employee ID 2 fall into?",
    ],
}


def format_examples() -> str:
    lines: list[str] = ["Template questions you can ask:", ""]
    for topic, questions in TEMPLATE_QUESTIONS.items():
        lines.append(f"## {topic}")
        for q in questions:
            lines.append(f"  - {q}")
        lines.append("")
    lines.append(
        "Note: With GDPR_PSEUDONYMIZE=true (default), name-based questions "
        "will not resolve. Use employee IDs with --role hr_admin."
    )
    return "\n".join(lines)
