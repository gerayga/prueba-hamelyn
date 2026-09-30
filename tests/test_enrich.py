from authors.enrich import count_references, pick_date


def claim(time, precision, rank="normal", refs=()):
    return {
        "rank": rank,
        "mainsnak": {"snaktype": "value", "datavalue": {"value": {
            "time": time, "precision": precision,
            "calendarmodel": "http://www.wikidata.org/entity/Q1985727"}}},
        "references": [{"snaks": {p: [] for p in r}} for r in refs],
    }


def test_preferred_rank_wins_over_more_precise_normal():
    date, conflict = pick_date([
        claim("+0973-00-00T00:00:00Z", 9),
        claim("+0970-00-00T00:00:00Z", 8, rank="preferred"),
    ])
    assert date["date"] == "0970" and date["precision"] == "decade" and not conflict


def test_deprecated_is_ignored():
    date, _ = pick_date([claim("+1900-01-01T00:00:00Z", 11, rank="deprecated"),
                         claim("+1901-00-00T00:00:00Z", 9)])
    assert date["year"] == 1901


def test_tie_broken_by_references_ignoring_p143():
    # Caso Ismat Chughtai: varias fechas de día con rango normal.
    date, conflict = pick_date([
        claim("+1911-08-21T00:00:00Z", 11, refs=[("P854", "P813")]),
        claim("+1915-08-21T00:00:00Z", 11, refs=[("P143",), ("P143",), ("P143",)]),
        claim("+1915-08-15T00:00:00Z", 11, refs=[("P854", "P813"), ("P248",)]),
    ])
    assert date["date"] == "1915-08-15" and conflict


def test_count_references_excludes_imported_from():
    assert count_references(claim("+1900-00-00T00:00:00Z", 9, refs=[("P143",), ("P248",)])) == 1


def test_unknown_value_is_skipped():
    unknown = {"rank": "normal", "mainsnak": {"snaktype": "somevalue"}}
    assert pick_date([unknown]) == (None, False)
