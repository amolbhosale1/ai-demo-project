from briefing_agent.config import merge_industry_preset


def test_merge_industry_preset_uses_preset_with_client_override():
    industries = {
        "industries": {
            "coding": {
                "keywords": ["software", "developer"],
                "rss_feeds": [{"name": "A", "url": "https://a.example/rss"}],
            }
        }
    }
    client = {
        "industry": {
            "name": "coding",
            "keywords": ["ai", "open source"],
        }
    }
    merged = merge_industry_preset(client, industries)
    assert merged["industry"]["rss_feeds"] == [{"name": "A", "url": "https://a.example/rss"}]
    assert merged["industry"]["keywords"] == ["ai", "open source"]

