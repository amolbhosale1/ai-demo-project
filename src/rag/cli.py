"""Typer CLI for company information RAG."""

from __future__ import annotations

import json
from typing import Literal, Optional

import typer

from rag.agent import answer_question
from rag.config import get_settings
from rag.ingest import build_vector_store, ingest_dataset
from rag.privacy.audit import AuditLogger
from rag.privacy.retention import RetentionPolicy
from rag.questions import format_examples

app = typer.Typer(
    help="Company information RAG (Ollama + Qdrant) with GDPR controls.",
    no_args_is_help=True,
)

RoleOpt = Literal["employee", "hr_admin", "dpo"]


def _audit() -> AuditLogger:
    settings = get_settings()
    return AuditLogger(settings.gdpr_audit_log_path, log_pii=settings.gdpr_query_log_pii)


def _require_role(role: str, allowed: set[str], action: str) -> None:
    if role not in allowed:
        typer.echo(
            f"Role '{role}' is not allowed to {action}. "
            f"Allowed: {', '.join(sorted(allowed))}",
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def ingest(
    recreate: bool = typer.Option(
        True,
        help="Recreate the Qdrant collection before ingesting (default: true).",
    ),
) -> None:
    """Load PDF + CSV dataset into Qdrant with pseudonymization."""
    settings = get_settings()
    typer.echo(f"Dataset: {settings.rag_dataset_dir}")
    typer.echo(f"Collection: {settings.qdrant_collection_name}")
    typer.echo(f"Pseudonymize: {settings.gdpr_pseudonymize}")
    typer.echo("Ingesting (this may take a while for embeddings)...")
    try:
        counts = ingest_dataset(settings=settings, recreate=recreate)
    except Exception as exc:
        typer.echo(f"Ingest failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"Done. documents={counts['documents']} "
        f"chunks={counts['chunks']} upserted={counts['upserted']}"
    )
    _audit().log(
        "ingest",
        settings.rag_default_role,
        documents=counts["documents"],
        chunks=counts["chunks"],
        upserted=counts["upserted"],
    )


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about company policy or workforce data."),
    role: Optional[str] = typer.Option(
        None,
        "--role",
        help="Access role: employee | hr_admin | dpo",
    ),
) -> None:
    """Ask a single question."""
    settings = get_settings()
    role = role or settings.rag_default_role
    if role not in ("employee", "hr_admin", "dpo"):
        typer.echo(f"Invalid role: {role}", err=True)
        raise typer.Exit(code=1)

    audit = _audit()
    audit.log_query(question, role)

    try:
        result = answer_question(question, role=role, settings=settings)
    except Exception as exc:
        typer.echo(f"Query failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(result.answer)
    if result.sources:
        typer.echo("\nSources:")
        for src in result.sources:
            typer.echo(f"  - {src}")
    if result.redactions_applied:
        typer.echo("\n[redactions applied]")


@app.command()
def chat(
    role: Optional[str] = typer.Option(
        None,
        "--role",
        help="Access role: employee | hr_admin | dpo",
    ),
) -> None:
    """Interactive question loop. Type 'exit' or 'quit' to stop."""
    settings = get_settings()
    role = role or settings.rag_default_role
    if role not in ("employee", "hr_admin", "dpo"):
        typer.echo(f"Invalid role: {role}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Company RAG chat (role={role}). Type exit/quit to leave.")
    audit = _audit()
    while True:
        try:
            question = typer.prompt("You")
        except (EOFError, KeyboardInterrupt):
            typer.echo("")
            break
        if question.strip().lower() in {"exit", "quit", "q"}:
            break
        if not question.strip():
            continue
        audit.log_query(question, role)
        try:
            result = answer_question(question, role=role, settings=settings)
            typer.echo(f"Assistant: {result.answer}")
            if result.redactions_applied:
                typer.echo("[redactions applied]")
        except Exception as exc:
            typer.echo(f"Query failed: {exc}", err=True)


@app.command()
def examples() -> None:
    """Print template questions grouped by topic and role."""
    typer.echo(format_examples())


@app.command("export")
def export_subject(
    employee_id: int = typer.Option(..., "--employee-id", help="Data subject employee_id."),
    role: str = typer.Option("dpo", "--role", help="Must be dpo or hr_admin."),
) -> None:
    """Export all Qdrant payloads for a subject (access / portability)."""
    _require_role(role, {"dpo", "hr_admin"}, "export subject data")
    store = build_vector_store()
    records = store.export_by_subject(employee_id)
    _audit().log_export(employee_id, role, len(records))
    typer.echo(json.dumps({"employee_id": employee_id, "records": records}, indent=2))


@app.command()
def erase(
    employee_id: int = typer.Option(..., "--employee-id", help="Data subject employee_id."),
    role: str = typer.Option("dpo", "--role", help="Must be dpo."),
    confirm: bool = typer.Option(False, "--confirm", help="Required to perform hard delete."),
) -> None:
    """Hard-delete all vectors for a subject (right to erasure)."""
    _require_role(role, {"dpo"}, "erase subject data")
    if not confirm:
        typer.echo(
            "Refusing to erase without --confirm. "
            "This permanently deletes vectors for the subject.",
            err=True,
        )
        raise typer.Exit(code=1)
    store = build_vector_store()
    deleted = store.delete_by_subject(employee_id)
    _audit().log_erasure(employee_id, role, deleted)
    typer.echo(f"Erased {deleted} point(s) for employee_id={employee_id}.")


@app.command()
def audit(
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="ISO date/datetime lower bound, e.g. 2026-01-01.",
    ),
    role: str = typer.Option("dpo", "--role", help="Must be dpo."),
) -> None:
    """Show audit trail events (accountability)."""
    _require_role(role, {"dpo"}, "view the audit log")
    events = _audit().read_since(since)
    typer.echo(json.dumps(events, indent=2))


@app.command("purge-expired")
def purge_expired(
    role: str = typer.Option("dpo", "--role", help="Must be dpo or hr_admin."),
) -> None:
    """Remove vectors past GDPR_RETENTION_DAYS (storage limitation)."""
    _require_role(role, {"dpo", "hr_admin"}, "purge expired vectors")
    settings = get_settings()
    cutoff = RetentionPolicy(settings.gdpr_retention_days).cutoff_iso()
    store = build_vector_store(settings)
    deleted = store.purge_before(cutoff)
    _audit().log("purge_expired", role, cutoff=cutoff, deleted=deleted)
    typer.echo(f"Purged {deleted} expired point(s) (cutoff={cutoff}).")


@app.command()
def version() -> None:
    """Print package version."""
    from rag import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
