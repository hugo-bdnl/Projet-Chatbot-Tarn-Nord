import pytest

from app.search.engine import reciprocal_rank_fusion


def test_rrf_rewards_documents_present_in_both_lists():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]], k=60)
    order = sorted(fused, key=fused.get, reverse=True)
    assert order[0] == "a"           # 1er + 2e
    assert order[1] == "c"           # 3e + 1er
    assert set(order[2:]) == {"b", "d"}
    assert fused["a"] == pytest.approx(1 / 61 + 1 / 62)


def test_rrf_handles_empty_lists():
    assert reciprocal_rank_fusion([]) == {}
    assert reciprocal_rank_fusion([[], ["x"]]) == {"x": pytest.approx(1 / 61)}
