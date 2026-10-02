"""
Smart subscription detection
Automatically identifies recurring charges
"""
from backend.utils.datetime import utcnow
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Common subscription merchants/patterns
COMMON_SUBSCRIPTIONS = {
    'netflix': {'name': 'Netflix', 'category': 'Entertainment', 'typical_range': (150, 500)},
    'spotify': {'name': 'Spotify', 'category': 'Entertainment', 'typical_range': (120, 300)},
    'amazon prime': {'name': 'Amazon Prime', 'category': 'Shopping', 'typical_range': (150, 1500)},
    'youtube': {'name': 'YouTube Premium', 'category': 'Entertainment', 'typical_range': (130, 250)},
    'chatgpt': {'name': 'ChatGPT Plus', 'category': 'Software', 'typical_range': (200, 300)},
    'gym': {'name': 'Gym Membership', 'category': 'Health', 'typical_range': (500, 3000)},
    'apple': {'name': 'Apple Subscription', 'category': 'Software', 'typical_range': (100, 2000)},
    'google': {'name': 'Google Cloud/One', 'category': 'Software', 'typical_range': (99, 500)},
    'microsoft': {'name': 'Microsoft 365', 'category': 'Software', 'typical_range': (600, 2000)},
    'dropbox': {'name': 'Dropbox', 'category': 'Software', 'typical_range': (500, 1000)},
    'slack': {'name': 'Slack', 'category': 'Software', 'typical_range': (600, 12500)},
    'notion': {'name': 'Notion', 'category': 'Software', 'typical_range': (800, 1200)},
    'figma': {'name': 'Figma', 'category': 'Software', 'typical_range': (1200, 2000)},
    'adobe': {'name': 'Adobe Creative Cloud', 'category': 'Software', 'typical_range': (4000, 8000)},
    'insurance': {'name': 'Insurance', 'category': 'Insurance', 'typical_range': (500, 10000)},
    'mobile': {'name': 'Mobile Plan', 'category': 'Utilities', 'typical_range': (300, 2000)},
    'internet': {'name': 'Internet/Broadband', 'category': 'Utilities', 'typical_range': (400, 3000)},
    'electric': {'name': 'Electricity Bill', 'category': 'Utilities', 'typical_range': (500, 5000)},
}


class SubscriptionDetector:
    """Detect recurring subscription charges"""
    
    @staticmethod
    def identify_recurring_merchants(
        transactions: List[Dict[str, Any]],
        min_occurrences: int = 2,
        days_lookback: int = 180
    ) -> Dict[str, Dict[str, Any]]:
        """
        Identify merchants with recurring patterns
        
        Args:
            transactions: List of transactions
            min_occurrences: Minimum times a merchant must appear
            days_lookback: How far back to look for patterns
        """
        try:
            cutoff_date = utcnow() - timedelta(days=days_lookback)
            
            # Filter recent transactions
            recent_txs = [
                tx for tx in transactions
                if datetime.fromisoformat(tx.get('date', '')) >= cutoff_date
                and tx.get('amount', 0) < 0  # Only expenses
            ]
            
            # Group by merchant
            merchant_txs = defaultdict(list)
            for tx in recent_txs:
                merchant = tx.get('merchant', 'Unknown').lower()
                merchant_txs[merchant].append(tx)
            
            # Analyze patterns
            recurring_merchants = {}
            
            for merchant, txs in merchant_txs.items():
                if len(txs) < min_occurrences:
                    continue
                
                # Sort by date
                sorted_txs = sorted(txs, key=lambda x: x.get('date', ''))
                
                # Calculate intervals between transactions
                intervals = []
                for i in range(len(sorted_txs) - 1):
                    try:
                        date1 = datetime.fromisoformat(sorted_txs[i].get('date', ''))
                        date2 = datetime.fromisoformat(sorted_txs[i+1].get('date', ''))
                        interval_days = (date2 - date1).days
                        intervals.append(interval_days)
                    except Exception:
                        continue
                
                if not intervals:
                    continue
                
                # Check for consistent intervals (within ±5 days)
                avg_interval = sum(intervals) / len(intervals)
                consistent_intervals = all(
                    abs(interval - avg_interval) <= 5 for interval in intervals
                )
                
                # Calculate amount consistency
                amounts = [abs(tx.get('amount', 0)) for tx in txs]
                avg_amount = sum(amounts) / len(amounts)
                amount_consistency = (
                    sum(1 for a in amounts if abs(a - avg_amount) <= avg_amount * 0.1)
                    / len(amounts)
                )
                
                if consistent_intervals or amount_consistency > 0.7:
                    recurring_merchants[merchant] = {
                        'merchant_name': merchant,
                        'occurrences': len(txs),
                        'average_amount': avg_amount,
                        'average_interval_days': avg_interval,
                        'is_consistent': consistent_intervals,
                        'consistency_score': amount_consistency,
                        'last_transaction': sorted_txs[-1].get('date'),
                        'all_transactions': sorted_txs
                    }
            
            return recurring_merchants
        
        except Exception as e:
            logger.error(f"Error identifying recurring merchants: {str(e)}")
            return {}
    
    @staticmethod
    def classify_subscriptions(
        recurring_merchants: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Classify recurring merchants as subscriptions and estimate savings
        """
        subscriptions = []
        
        for merchant, pattern in recurring_merchants.items():
            # Check if merchant matches known subscription
            matched_subscription = None
            for key, subscription_info in COMMON_SUBSCRIPTIONS.items():
                if key in merchant:
                    matched_subscription = subscription_info
                    break
            
            # Determine cycle based on interval
            interval = pattern['average_interval_days']
            if 25 <= interval <= 35:
                cycle = 'monthly'
                cycles_per_year = 12
            elif 85 <= interval <= 95:
                cycle = 'quarterly'
                cycles_per_year = 4
            elif 350 <= interval <= 370:
                cycle = 'yearly'
                cycles_per_year = 1
            elif 5 <= interval <= 8:
                cycle = 'weekly'
                cycles_per_year = 52
            else:
                cycle = 'irregular'
                cycles_per_year = 12 / (interval / 30) if interval > 0 else 1
            
            amount = pattern['average_amount']
            
            # Estimate monthly cost
            if cycle == 'monthly':
                monthly_cost = amount
            elif cycle == 'quarterly':
                monthly_cost = amount / 3
            elif cycle == 'yearly':
                monthly_cost = amount / 12
            elif cycle == 'weekly':
                monthly_cost = amount * 4.33
            else:
                monthly_cost = amount * (12 / (interval / 30)) if interval > 0 else amount
            
            annual_cost = monthly_cost * 12
            
            subscription = {
                'merchant': merchant,
                'name': matched_subscription['name'] if matched_subscription else merchant.title(),
                'category': matched_subscription['category'] if matched_subscription else 'Subscriptions',
                'amount_per_cycle': amount,
                'cycle': cycle,
                'monthly_cost': monthly_cost,
                'annual_cost': annual_cost,
                'occurrences': pattern['occurrences'],
                'consistency_score': pattern['consistency_score'],
                'last_transaction_date': pattern['last_transaction'],
                'is_known_service': matched_subscription is not None,
                'matched_known': matched_subscription is not None,
            }
            
            subscriptions.append(subscription)
        
        return sorted(subscriptions, key=lambda x: x['annual_cost'], reverse=True)
    
    @staticmethod
    def generate_recommendations(
        subscriptions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate subscription management recommendations
        """
        recommendations = []
        
        # Total monthly spend on subscriptions
        total_monthly = sum(sub['monthly_cost'] for sub in subscriptions)
        total_annual = sum(sub['annual_cost'] for sub in subscriptions)
        
        # Add summary recommendation
        if total_annual > 50000:
            recommendations.append({
                'type': 'total_spend',
                'severity': 'high',
                'message': f"You're spending ₹{total_annual:,.0f} per year on subscriptions. Review and cancel unused services.",
                'potential_savings': total_annual * 0.2  # Assume 20% can be cut
            })
        
        # Low-usage subscription detection
        for sub in subscriptions:
            if sub['consistency_score'] < 0.5:
                recommendations.append({
                    'type': 'low_usage',
                    'service': sub['name'],
                    'severity': 'medium',
                    'message': f"{sub['name']} appears unused. Consider cancelling to save ₹{sub['annual_cost']:,.0f}/year.",
                    'potential_savings': sub['annual_cost']
                })
            
            # High-cost recommendations
            if sub['annual_cost'] > 20000:
                recommendations.append({
                    'type': 'high_cost',
                    'service': sub['name'],
                    'severity': 'medium',
                    'message': f"{sub['name']} costs ₹{sub['annual_cost']:,.0f}/year. Check if cheaper alternatives exist.",
                    'potential_savings': sub['annual_cost'] * 0.3
                })
        
        # Bundle recommendations
        netflix_found = any('netflix' in sub['merchant'] for sub in subscriptions)
        prime_found = any('amazon' in sub['merchant'] for sub in subscriptions)
        
        if netflix_found and prime_found:
            recommendations.append({
                'type': 'bundle_opportunity',
                'severity': 'low',
                'message': "Consider bundling streaming services for better value.",
                'potential_savings': 2000
            })
        
        return sorted(
            recommendations,
            key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x['severity'], 0),
            reverse=True
        )


async def detect_subscriptions(
    transactions: List[Dict[str, Any]],
    user_id: str = None
) -> Dict[str, Any]:
    """
    Main function to detect subscriptions and generate recommendations
    """
    try:
        detector = SubscriptionDetector()
        
        # Identify recurring merchants
        recurring = detector.identify_recurring_merchants(transactions)
        
        # Classify as subscriptions
        subscriptions = detector.classify_subscriptions(recurring)
        
        # Generate recommendations
        recommendations = detector.generate_recommendations(subscriptions)
        
        # Calculate totals
        total_monthly = sum(sub['monthly_cost'] for sub in subscriptions)
        total_annual = sum(sub['annual_cost'] for sub in subscriptions)
        
        return {
            'user_id': user_id,
            'subscriptions': subscriptions,
            'total_count': len(subscriptions),
            'total_monthly_cost': total_monthly,
            'total_annual_cost': total_annual,
            'recommendations': recommendations,
            'potential_annual_savings': sum(
                rec.get('potential_savings', 0) for rec in recommendations
            ),
            'timestamp': utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in detect_subscriptions: {str(e)}")
        return {
            'error': str(e),
            'subscriptions': [],
            'recommendations': []
        }
