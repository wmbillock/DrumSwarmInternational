from collections import Counter

from backend.services.achievement_catalog import load_achievement_catalog


def test_achievement_catalog_counts():
    catalog = load_achievement_catalog()
    assert len(catalog) == 360
    counts = Counter(a.category for a in catalog)
    assert len(counts) == 12
    assert all(count == 30 for count in counts.values())
