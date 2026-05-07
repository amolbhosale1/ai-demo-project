from pathlib import Path

from briefing_agent.output.docx_writer import write_docx
from briefing_agent.types import BriefingItem


def test_docx_writer_creates_file(tmp_path: Path):
    items = [
        BriefingItem(
            title="Sample Article",
            url="https://example.com/article",
            summary="Article summary",
            source_name="TestSource",
            source_type="rss",
            category="article",
        ),
        BriefingItem(
            title="GDP Data",
            url="https://example.com/data",
            summary="GDP rose to X in 2024",
            source_name="World Bank",
            source_type="api",
            category="data_point",
        ),
    ]
    out = write_docx(
        output_dir=tmp_path,
        client_name="Test Client",
        summary="Weekly summary text.",
        approved_items=items,
        mix_counts={"rss": 1, "api": 1, "other": 0},
    )
    assert out.exists()
    assert out.suffix == ".docx"

