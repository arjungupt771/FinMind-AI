"""
Advanced anomaly detection for financial transactions
Uses Isolation Forest and statistical methods
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from backend.utils.datetime import utcnow
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def _tx_key(tx: Dict[str, Any]) -> str:
    """Stable identity for a transaction dict, whether or not it has a DB id."""
    if tx.get('id'):
        return str(tx['id'])
    return f"{tx.get('date', '')}|{tx.get('merchant', '')}|{tx.get('amount', '')}"


def _coefficient_of_variation(values: np.ndarray) -> float:
    mean = np.mean(values)
    if mean == 0:
        return 0.0
    return float(np.std(values) / abs(mean))

def _robust_z_scores(values: np.ndarray) -> np.ndarray:
    """
    Median/MAD-based z-score. Unlike mean/std, this isn't distorted by the
    outliers it's trying to detect (a single spike can't inflate the median
    or drag the MAD the way it drags a mean/std).
    """
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    if mad == 0:
        # Fall back to a small epsilon scaled to the data so we don't divide by zero
        # when every value in the window is identical.
        mad = max(np.std(values), 1e-6)
    # 0.6745 makes MAD comparable to a standard deviation under a normal distribution,
    # so existing threshold_std values (e.g. 2.0, 3.0) stay meaningful.
    return 0.6745 * (values - median) / mad


class AnomalyDetector:
    """Detect anomalies in financial transactions"""

    def __init__(self, contamination: float = 0.05):
        """
        Args:
            contamination: Expected proportion of anomalies (0-1)
        """
        self.contamination = contamination
        self.scaler = StandardScaler()

    def detect_spending_spikes(
        self,
        transactions: List[Dict[str, Any]],
        category: str = None,
        threshold_std: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect unusual spending spikes using a robust (median/MAD) z-score."""
        if not transactions:
            return []

        try:
            if category:
                txs = [tx for tx in transactions if tx.get('category') == category and tx.get('amount', 0) < 0]
            else:
                txs = [tx for tx in transactions if tx.get('amount', 0) < 0]

            if len(txs) < 3:
                return []

            amounts = np.array([abs(tx.get('amount', 0)) for tx in txs])
            z_scores = _robust_z_scores(amounts)

            spikes = []
            for tx, z_score in zip(txs, z_scores):
                if z_score > threshold_std:
                    spikes.append({
                        'transaction': tx,
                        'z_score': float(z_score),
                        'anomaly_reason': f'Spending spike: {z_score:.1f}σ above median (robust)',
                        'severity': 'high' if z_score > 3 else 'medium',
                        'normalized_score': float(min(z_score / 6.0, 1.0)),
                    })

            return sorted(spikes, key=lambda x: x['z_score'], reverse=True)

        except Exception as e:
            logger.error(f"Error detecting spending spikes: {str(e)}")
            return []

    def detect_duplicate_transactions(
        self,
        transactions: List[Dict[str, Any]],
        time_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Detect potential duplicate transactions"""
        if not transactions:
            return []

        duplicates = []
        sorted_txs = sorted(transactions, key=lambda x: x.get('date', ''))

        for i, tx1 in enumerate(sorted_txs):
            for tx2 in sorted_txs[i + 1:]:
                try:
                    date1 = datetime.fromisoformat(tx1.get('date', ''))
                    date2 = datetime.fromisoformat(tx2.get('date', ''))
                    time_diff = abs((date2 - date1).total_seconds()) / 3600

                    amount_match = abs(tx1.get('amount', 0) - tx2.get('amount', 0)) < 0.01
                    merchant_match = tx1.get('merchant', '') == tx2.get('merchant', '')
                    category_match = tx1.get('category', '') == tx2.get('category', '')

                    if amount_match and merchant_match and time_diff < time_window_hours:
                        duplicates.append({
                            'transaction_1': tx1,
                            'transaction_2': tx2,
                            'time_diff_hours': float(time_diff),
                            'confidence': 0.95 if category_match else 0.85
                        })
                except Exception:
                    continue

        return duplicates

    def detect_fraud_patterns(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rule-based fraud-like pattern detection:
        - Rapid repeated transactions to the same merchant
        - Unusually large first-time transaction with a new merchant
        """
        if not transactions:
            return []

        fraud_indicators = []

        try:
            merchants = {}
            for tx in transactions:
                merchant = tx.get('merchant', 'Unknown')
                merchants.setdefault(merchant, []).append(tx)

            for merchant, txs in merchants.items():
                if len(txs) >= 3:
                    sorted_txs = sorted(txs, key=lambda x: x.get('date', ''))
                    for i in range(len(sorted_txs) - 2):
                        try:
                            t1 = datetime.fromisoformat(sorted_txs[i].get('date', ''))
                            t2 = datetime.fromisoformat(sorted_txs[i + 1].get('date', ''))
                            t3 = datetime.fromisoformat(sorted_txs[i + 2].get('date', ''))

                            diff1 = (t2 - t1).total_seconds() / 60
                            diff2 = (t3 - t2).total_seconds() / 60

                            if diff1 < 30 and diff2 < 30:
                                fraud_indicators.append({
                                    'type': 'rapid_transactions',
                                    'merchant': merchant,
                                    'transactions': [sorted_txs[i], sorted_txs[i + 1], sorted_txs[i + 2]],
                                    'time_window_minutes': 60,
                                    'risk_score': 0.7
                                })
                        except Exception:
                            continue

            expense_txs = [tx for tx in transactions if tx.get('amount', 0) < 0]
            if expense_txs:
                amounts = np.array([abs(tx.get('amount', 0)) for tx in expense_txs])
                median = np.median(amounts)  # robust reference point, same reasoning as spikes above
                median = median if median > 0 else np.mean(amounts) or 1.0

                for tx in expense_txs:
                    amount = abs(tx.get('amount', 0))
                    if amount > median * 3:
                        merchant_history = [t for t in transactions if t.get('merchant') == tx.get('merchant')]
                        if len(merchant_history) == 1:
                            fraud_indicators.append({
                                'type': 'large_amount_new_merchant',
                                'transaction': tx,
                                'amount': amount,
                                'multiple_of_median': amount / median,
                                'risk_score': 0.6
                            })

        except Exception as e:
            logger.error(f"Error detecting fraud patterns: {str(e)}")

        return fraud_indicators

    def detect_category_outliers(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect transactions that are IQR outliers within their own category"""
        if not transactions:
            return []

        outliers = []
        expense_txs = [tx for tx in transactions if tx.get('amount', 0) < 0]

        by_category: Dict[str, List[float]] = {}
        for tx in expense_txs:
            by_category.setdefault(tx.get('category', 'Other'), []).append(abs(tx.get('amount', 0)))

        bounds_by_category = {}
        for category, amounts in by_category.items():
            if len(amounts) < 3:
                continue
            arr = np.array(amounts)
            q1, q3 = np.percentile(arr, [25, 75])
            iqr = q3 - q1
            bounds_by_category[category] = (q1 - 1.5 * iqr, q3 + 1.5 * iqr, iqr)

        for tx in expense_txs:
            category = tx.get('category', 'Other')
            bounds = bounds_by_category.get(category)
            if not bounds:
                continue
            lower_bound, upper_bound, iqr = bounds
            amount = abs(tx.get('amount', 0))
            if amount > upper_bound or amount < lower_bound:
                threshold = upper_bound if amount > upper_bound else lower_bound
                distance = abs(amount - threshold)
                normalized_score = float(min(distance / (iqr + 1e-6) / 3.0, 1.0)) if iqr > 0 else 0.5
                outliers.append({
                    'transaction': tx,
                    'category': category,
                    'amount': amount,
                    'threshold': threshold,
                    'outlier_type': 'high' if amount > upper_bound else 'low',
                    'normalized_score': normalized_score,
                })

        return outliers

    def detect_sudden_merchant_change(
        self,
        transactions: List[Dict[str, Any]],
        category: str,
        lookback_days: int = 90
    ) -> List[Dict[str, Any]]:
        """Detect when a user suddenly changes merchants in a category"""
        if not transactions:
            return []

        try:
            cutoff_date = utcnow() - timedelta(days=lookback_days)
            recent_txs = [
                tx for tx in transactions
                if tx.get('date') and datetime.fromisoformat(tx['date']) >= cutoff_date
                and tx.get('category') == category
            ]

            if len(recent_txs) < 5:
                return []

            first_half = [tx.get('merchant') for tx in recent_txs[:len(recent_txs) // 2]]
            second_half = [tx.get('merchant') for tx in recent_txs[len(recent_txs) // 2:]]

            most_common_first = max(set(first_half), key=first_half.count) if first_half else None
            most_common_second = max(set(second_half), key=second_half.count) if second_half else None

            if most_common_first and most_common_second and most_common_first != most_common_second:
                return [{
                    'category': category,
                    'old_merchant': most_common_first,
                    'new_merchant': most_common_second,
                    'change_type': 'merchant_change',
                    'transactions': second_half.count(most_common_second)
                }]

            return []

        except Exception as e:
            logger.error(f"Error detecting merchant changes: {str(e)}")
            return []


    def detect_merchant_behavior_anomalies(
        self,
        transactions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        if not transactions:
            return []

        merchant_history: Dict[str, List[float]] = {}

        for tx in transactions:
            if tx.get("amount", 0) >= 0:
                continue

            merchant = str(
                tx.get("merchant", "Unknown")
            ).strip()

            try:
                amount = abs(float(tx.get("amount", 0)))
            except (TypeError, ValueError):
                continue

            if amount <= 0:
                continue

            merchant_history.setdefault(
                merchant,
                [],
            ).append(amount)

        anomalies = []

        for tx in transactions:
            if tx.get("amount", 0) >= 0:
                continue

            merchant = str(
                tx.get("merchant", "Unknown")
            ).strip()

            history = merchant_history.get(
                merchant,
                [],
            )

            if len(history) < 3:
                continue

            try:
                amount = abs(float(tx.get("amount", 0)))
            except (TypeError, ValueError):
                continue

            baseline = np.median(history)

            if baseline <= 0:
                continue

            multiple = amount / baseline

            if multiple >= 3:
                score = min(
                    1.0,
                    0.45 + (multiple - 3) / 10,
                )

                anomalies.append({
                    "transaction": tx,
                    "merchant": merchant,
                    "historical_median": round(
                        float(baseline),
                        2,
                    ),
                    "amount": round(
                        float(amount),
                        2,
                    ),
                    "multiple_of_baseline": round(
                        float(multiple),
                        2,
                    ),
                    "normalized_score": round(
                        float(score),
                        3,
                    ),
                    "anomaly_reason": (
                        "Transaction is unusually large "
                        "for this merchant"
                    ),
                })

        return sorted(
            anomalies,
            key=lambda x: x["normalized_score"],
            reverse=True,
        )

    def detect_spending_velocity_anomalies(
        self,
        transactions: List[Dict[str, Any]],
        window_hours: int = 24,
        minimum_transactions: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Detect unusually dense spending activity.

        Example:
        several expense transactions within a short period can indicate
        duplicate charges, unusual activity, or a burst in spending.
        """

        if not transactions:
            return []

        parsed = []

        for tx in transactions:
            if tx.get("amount", 0) >= 0:
                continue

            raw_date = tx.get("date")

            if not raw_date:
                continue

            try:
                if isinstance(raw_date, datetime):
                    date = raw_date
                else:
                    date = datetime.fromisoformat(
                        str(raw_date).replace(
                            "Z",
                            "+00:00",
                        )
                    )

                parsed.append((date, tx))

            except (TypeError, ValueError):
                continue

        parsed.sort(key=lambda item: item[0])

        anomalies = []

        for i, (start_date, start_tx) in enumerate(parsed):
            window_end = start_date + timedelta(
                hours=window_hours
            )

            window = [
                tx
                for date, tx in parsed[i:]
                if date <= window_end
            ]

            if len(window) < minimum_transactions:
                continue

            total_amount = sum(
                abs(float(tx.get("amount", 0)))
                for tx in window
            )

            density_score = min(
                1.0,
                len(window) / 10.0,
            )

            amount_score = min(
                1.0,
                total_amount / 5000.0,
            )

            score = min(
                1.0,
                density_score * 0.6
                + amount_score * 0.4,
            )

            anomalies.append({
                "start_transaction": start_tx,
                "transactions": window,
                "transaction_count": len(window),
                "total_amount": round(
                    total_amount,
                    2,
                ),
                "window_hours": window_hours,
                "normalized_score": round(
                    score,
                    3,
                ),
                "anomaly_reason": (
                    f"Unusually high spending velocity: "
                    f"{len(window)} transactions within "
                    f"{window_hours} hours"
                ),
            })

        # Remove overlapping windows by keeping the strongest one.
        anomalies.sort(
            key=lambda x: x["normalized_score"],
            reverse=True,
        )

        return anomalies[:20]

    def detect_unusual_transaction_times(
        self,
        transactions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Detect expense transactions occurring at unusual hours.

        Late-night activity is only treated as a signal, not proof of fraud.
        """

        if not transactions:
            return []

        expense_times = []

        for tx in transactions:
            if tx.get("amount", 0) >= 0:
                continue

            raw_date = tx.get("date")

            if not raw_date:
                continue

            try:
                if isinstance(raw_date, datetime):
                    date = raw_date
                else:
                    date = datetime.fromisoformat(
                        str(raw_date).replace(
                            "Z",
                            "+00:00",
                        )
                    )

                expense_times.append(date.hour)

            except (TypeError, ValueError):
                continue

        if len(expense_times) < 5:
            return []

        # Build hourly frequency.
        hour_counts = {}

        for hour in expense_times:
            hour_counts[hour] = (
                hour_counts.get(hour, 0) + 1
            )

        total = len(expense_times)

        anomalies = []

        for tx in transactions:
            if tx.get("amount", 0) >= 0:
                continue

            raw_date = tx.get("date")

            try:
                if isinstance(raw_date, datetime):
                    date = raw_date
                else:
                    date = datetime.fromisoformat(
                        str(raw_date).replace(
                            "Z",
                            "+00:00",
                        )
                    )
            except (TypeError, ValueError):
                continue

            hour = date.hour
            frequency = hour_counts.get(
                hour,
                0,
            ) / total

            # 00:00-05:00 transactions are inherently worth
            # flagging as contextual signals.
            if 0 <= hour <= 5 and frequency <= 0.20:
                anomalies.append({
                    "transaction": tx,
                    "hour": hour,
                    "hour_frequency": round(
                        frequency,
                        3,
                    ),
                    "normalized_score": 0.45,
                    "anomaly_reason": (
                        "Transaction occurred during an "
                        "unusual late-night spending period"
                    ),
                })

        return anomalies

    def run_isolation_forest(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect unusual transactions using Isolation Forest.

        Features:
        - absolute transaction amount
        - hour of day
        - day of week

        The raw Isolation Forest decision score is converted into a
        percentile-based normalized anomaly score.

        Important:
        Isolation Forest can flag relatively unusual points even in a
        very uniform dataset. Severity therefore also considers the
        transaction's robust amount z-score.
        """

        if not transactions:
            return []

        try:
            kept_txs = []
            feature_rows = []

            for tx in transactions:
                raw_date = tx.get("date")
                amount = tx.get("amount", 0)

                if raw_date is None:
                    continue

                try:
                    tx_date = datetime.fromisoformat(str(raw_date))
                except (ValueError, TypeError):
                    continue

                try:
                    amount = float(amount)
                except (TypeError, ValueError):
                    continue

                kept_txs.append(tx)

                feature_rows.append([
                    abs(amount),
                    tx_date.hour,
                    tx_date.weekday(),
                ])

            if len(kept_txs) < 5:
                return []

            features_array = np.asarray(feature_rows, dtype=float)

            # Standardize features before Isolation Forest.
            #
            # This prevents the raw amount scale from completely dominating
            # the temporal features.
            features_scaled = self.scaler.fit_transform(features_array)

            model = IsolationForest(
                contamination=min(
                    max(self.contamination, 0.01),
                    0.5,
                ),
                random_state=42,
                n_estimators=200,
            )

            predictions = model.fit_predict(features_scaled)

            # Higher decision_function values mean "more normal".
            # Negating it makes higher values represent "more anomalous".
            raw_scores = -model.decision_function(features_scaled)

            # Convert anomaly scores into a 0-1 percentile scale.
            percentiles = pd.Series(raw_scores).rank(
                pct=True,
                method="average",
            ).to_numpy()

            normalized_scores = np.clip(percentiles, 0.0, 1.0)

            # Column 0 = absolute transaction amount.
            amount_z_scores = _robust_z_scores(features_array[:, 0])

            anomalies = []

            for (
                tx,
                prediction,
                raw_score,
                norm_score,
                amount_z,
            ) in zip(
                kept_txs,
                predictions,
                raw_scores,
                normalized_scores,
                amount_z_scores,
            ):
                if prediction != -1:
                    continue

                # Isolation Forest alone should not classify a transaction
                # as "high" severity simply because it is slightly unusual.
                #
                # A high-severity financial anomaly requires both:
                #   1. a strong Isolation Forest signal
                #   2. a meaningful absolute amount deviation
                if norm_score > 0.9 and abs(amount_z) > 1.0:
                    severity = "high"
                elif norm_score > 0.9:
                    severity = "medium"
                else:
                    severity = "medium" if norm_score > 0.7 else "low"

                anomalies.append({
                    "transaction": tx,
                    "raw_score": float(raw_score),
                    "normalized_score": float(norm_score),
                    "amount_z_score": float(amount_z),
                    "method": "isolation_forest",
                    "severity": severity,
                })

            return sorted(
                anomalies,
                key=lambda x: x["normalized_score"],
                reverse=True,
            )

        except Exception as e:
            logger.error(
                f"Error running isolation forest: {str(e)}",
                exc_info=True,
            )
            return []

    def score_transactions(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine every detector's signal into one calibrated 0-1 anomaly
        score per transaction.

        If multiple detectors flag the same transaction, the highest
        normalized signal wins while all contributing reasons are retained.
        """

        if not transactions:
            return []

        per_tx: Dict[str, Dict[str, Any]] = {}

        def _accumulate(
            tx: Dict[str, Any],
            score: float,
            reason: str,
        ):
            key = _tx_key(tx)

            entry = per_tx.setdefault(
                key,
                {
                    "transaction": tx,
                    "score": 0.0,
                    "reasons": [],
                },
            )

            entry["reasons"].append({
                "reason": reason,
                "score": round(float(score), 3),
            })

            entry["score"] = max(
                entry["score"],
                float(score),
            )

        for spike in self.detect_spending_spikes(transactions):
            _accumulate(
                spike["transaction"],
                spike["normalized_score"],
                spike["anomaly_reason"],
            )

        for outlier in self.detect_category_outliers(transactions):
            _accumulate(
                outlier["transaction"],
                outlier["normalized_score"],
                (
                    f"{outlier['outlier_type']}-side outlier "
                    f"in category '{outlier['category']}'"
                ),
            )

        for fraud in self.detect_fraud_patterns(transactions):
            if fraud["type"] == "large_amount_new_merchant":
                _accumulate(
                    fraud["transaction"],
                    fraud["risk_score"],
                    "large first-time charge with new merchant",
                )

            elif fraud["type"] == "rapid_transactions":
                for tx in fraud["transactions"]:
                    _accumulate(
                        tx,
                        fraud["risk_score"],
                        (
                            f"rapid repeated charges "
                            f"at {fraud['merchant']}"
                        ),
                    )

                # ---------------------------------------------------------
        # Phase 5: contextual merchant intelligence
        # ---------------------------------------------------------

        for anomaly in self.detect_merchant_behavior_anomalies(
            transactions
        ):
            _accumulate(
                anomaly["transaction"],
                anomaly["normalized_score"],
                anomaly["anomaly_reason"],
            )

        # ---------------------------------------------------------
        # Phase 5: spending velocity intelligence
        # ---------------------------------------------------------

        for anomaly in self.detect_spending_velocity_anomalies(
            transactions
        ):
            for tx in anomaly["transactions"]:
                _accumulate(
                    tx,
                    anomaly["normalized_score"],
                    anomaly["anomaly_reason"],
                )

        # ---------------------------------------------------------
        # Phase 5: unusual transaction timing
        # ---------------------------------------------------------

        for anomaly in self.detect_unusual_transaction_times(
            transactions
        ):
            _accumulate(
                anomaly["transaction"],
                anomaly["normalized_score"],
                anomaly["anomaly_reason"],
            )

        ranked = sorted(
            per_tx.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        for entry in ranked:
            score = entry["score"]

            entry["severity"] = (
                "high"
                if score > 0.7
                else "medium"
                if score > 0.4
                else "low"
            )

        return ranked


async def detect_all_anomalies(transactions: List[Dict[str, Any]], user_id: str = None) -> Dict[str, Any]:
    try:
        detector = AnomalyDetector()

        results = {
            'spending_spikes': detector.detect_spending_spikes(transactions),
            'duplicates': detector.detect_duplicate_transactions(transactions),
            'fraud_patterns': detector.detect_fraud_patterns(transactions),
            'category_outliers': detector.detect_category_outliers(transactions),
            'isolation_forest_anomalies': detector.run_isolation_forest(transactions),
            'merchant_behavior_anomalies': detector.detect_merchant_behavior_anomalies(transactions),
            'spending_velocity_anomalies': detector.detect_spending_velocity_anomalies(transactions),
            'unusual_time_anomalies': detector.detect_unusual_transaction_times(transactions),
        }
        ranked_transactions = detector.score_transactions(transactions)

        expense_amounts = np.array([
            abs(tx.get('amount', 0)) for tx in transactions if tx.get('amount', 0) < 0
        ])
        cv = _coefficient_of_variation(expense_amounts) if len(expense_amounts) > 0 else 0.0
        dataset_variability = {
            'amount_coefficient_of_variation': round(cv, 3),
            'low_variability_warning': cv < 0.2,
            'note': (
                "This user's expense amounts are quite uniform — flagged anomalies here "
                "are relatively unusual for this person, not necessarily large in absolute terms."
                if cv < 0.2 else None
            ),
        }

        return {
            'user_id': user_id,
            'total_anomalies': len(ranked_transactions),
            'timestamp': utcnow().isoformat(),
            'results': results,
            'ranked_transactions': ranked_transactions,
            'dataset_variability': dataset_variability,
        }

    except Exception as e:
        logger.error(f"Error in detect_all_anomalies: {str(e)}")
        return {'error': str(e), 'results': {}, 'ranked_transactions': [], 'dataset_variability': {}}