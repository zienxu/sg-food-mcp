import data


def ids(query):
    return [h["id"] for h in data.search(query, limit=3)]


def test_ckt_alias():
    assert "char-kway-teow" in ids("ckt")


def test_kopi_o_kosong_peng():
    assert "iced-kopi-o-kosong" in ids("kopi o kosong peng")


def test_chicken_rice():
    # No dish is named exactly "chicken rice" — 5 variants exist and
    # search_dishes's own docstring treats returning several as correct
    # ("never average variants"), so any chicken-rice match in the top 3 is right.
    assert any("chicken-rice" in i for i in ids("chicken rice"))


def test_laksa():
    assert "laksa" in ids("laksa")
