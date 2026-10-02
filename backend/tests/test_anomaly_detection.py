from backend.analytics.anomaly_detection import AnomalyDetector, _robust_z_scores
import numpy as np


def _tx(date, amount, category="Food", merchant="M", tx_id=None):
    d = {"date": date, "amount": amount, "category": category, "merchant": merchant}
    if tx_id:
        d["id"] = tx_id
    return d


def test_robust_z_scores_not_masked_by_the_outlier_itself():
    # A single huge outlier shouldn't collapse everyone else's z-score toward zero,
    # the way mean/std would.
    values = np.array([100, 105, 98, 102, 101, 5000])
    z = _robust_z_scores(values)
    assert z[-1] > 3  # the outlier is still clearly flagged
    assert abs(z[0]) < 1  # the normal values stay near zero


def test_detect_spending_spikes_flags_large_outlier():
    detector = AnomalyDetector()
    transactions = [_tx(f"2026-01-{d:02d}T00:00:00", -100) for d in range(1, 10)]
    transactions.append(_tx("2026-01-10T00:00:00", -5000))
    spikes = detector.detect_spending_spikes(transactions)
    assert len(spikes) == 1
    assert spikes[0]['transaction']['amount'] == -5000
    assert 0 <= spikes[0]['normalized_score'] <= 1


def test_detect_category_outliers_normalized_score_bounded():
    detector = AnomalyDetector()
    transactions = [_tx(f"2026-01-{d:02d}T00:00:00", -100, category="Food") for d in range(1, 10)]
    transactions.append(_tx("2026-01-10T00:00:00", -3000, category="Food"))
    outliers = detector.detect_category_outliers(transactions)
    assert len(outliers) == 1
    assert 0 <= outliers[0]['normalized_score'] <= 1


def test_score_transactions_deduplicates_across_detectors():
    detector = AnomalyDetector()
    # A transaction that will be caught by BOTH the spike detector AND the category
    # outlier detector should appear exactly once in the combined ranking.
    transactions = [_tx(f"2026-01-{d:02d}T00:00:00", -100, category="Food", tx_id=f"tx{d}") for d in range(1, 10)]
    transactions.append(_tx("2026-01-10T00:00:00", -5000, category="Food", tx_id="tx-spike"))

    ranked = detector.score_transactions(transactions)
    matching = [r for r in ranked if r['transaction'].get('id') == 'tx-spike']
    assert len(matching) == 1
    assert len(matching[0]['reasons']) >= 1
    assert matching[0]['severity'] in ('low', 'medium', 'high')


def test_score_transactions_empty_input():
    detector = AnomalyDetector()
    assert detector.score_transactions([]) == []

def test_isolation_forest_requires_absolute_signal_for_high_severity():
    import numpy as np
    np.random.seed(1)
    detector = AnomalyDetector()
    # Perfectly uniform amounts (zero variance) at varied times: isolation forest may
    # still flag SOMETHING as relatively least-typical, but none should read as "high"
    # severity since no amount actually deviates.
    transactions = [
        _tx(f"2026-01-{(d % 28) + 1:02d}T{(d * 3) % 24:02d}:00:00", -100, category="Food", merchant="M")
        for d in range(1, 30)
    ]
    anomalies = detector.run_isolation_forest(transactions)
    assert all(a['severity'] != 'high' for a in anomalies)


import asyncio


def test_detect_all_anomalies_flags_low_variability_dataset():
    transactions = [
        _tx(
            f"2026-01-{d:02d}T00:00:00",
            -100,
        )
        for d in range(1, 15)
    ]

    from backend.analytics.anomaly_detection import detect_all_anomalies

    result = asyncio.run(
        detect_all_anomalies(transactions)
    )

    assert result["dataset_variability"]["low_variability_warning"] is True