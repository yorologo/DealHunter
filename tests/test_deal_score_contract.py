import json
from pathlib import Path

from dealhunter.score import DEAL_SCORE_ALGORITHM_VERSION, calculate_deal_score


CORPUS = Path(__file__).parent / "corpus" / "deal_score_v1.json"


def test_deal_score_version_is_explicit():
    assert DEAL_SCORE_ALGORITHM_VERSION == "deal-score-v1"


def test_deal_score_v1_regression_corpus():
    cases = json.loads(CORPUS.read_text())
    assert len(cases) >= 6
    for case in cases:
        actual = calculate_deal_score(
            case["metrics"],
            current_price=case["current_price"],
            original_price=case["original_price"],
            market_prices=case["market_prices"],
        )
        assert actual == case["expected"], case["name"]
