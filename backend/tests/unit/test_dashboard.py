from app.routes.dashboard import _best_baseline


def test_best_baseline_picks_higher_recovered_paise():
    name, recovered, yield_ = _best_baseline(
        {
            "naive": {"revenue_recovered_paise": 1000, "recovery_yield": 0.1},
            "rule_based": {"revenue_recovered_paise": 2500, "recovery_yield": 0.2},
        }
    )
    assert name == "rule_based"
    assert recovered == 2500
    assert yield_ == 0.2


def test_best_baseline_empty():
    assert _best_baseline({}) == (None, None, None)
