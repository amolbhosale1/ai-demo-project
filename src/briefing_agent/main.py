from __future__ import annotations

from pathlib import Path

import typer

from briefing_agent.config import ensure_source_providers, load_yaml, merge_industry_preset
from briefing_agent.graph import build_graph

app = typer.Typer(help="LangGraph Weekly Briefing Agent")


@app.command()
def run(client_config: str = typer.Option(..., help="Path to client YAML config")):
    cfg_path = Path(client_config)
    cfg = load_yaml(cfg_path)
    industries_path = Path("config/industries.yaml")
    if industries_path.exists():
        cfg = merge_industry_preset(cfg, load_yaml(industries_path))
    cfg = ensure_source_providers(cfg)
    graph = build_graph()
    initial_state = {
        "client_config": cfg,
        "raw_items": [],
        "ranked_items": [],
        "suggested_items": [],
        "approved_items": [],
        "briefing_summary": "",
        "output_path": "",
        "mix_counts": {},
    }
    result = graph.invoke(initial_state)
    typer.echo(f"Briefing generated: {result['output_path']}")


@app.command()
def version():
    """Show CLI version."""
    typer.echo("langgraph-weekly-briefing-agent 0.1.0")


if __name__ == "__main__":
    app()

