import pandas as pd
import numpy as np
from src import config

def compute_distributions(df):
    """
    Computes standard distributions for categories, sentiment, and sources.
    Includes representative customer feedback text examples per category.
    """
    results = {}
    
    # Category
    cat_counts = df['ai_category'].value_counts()
    category_dist = {}
    for cat in config.ALLOWED_CATEGORIES:
        count = int(cat_counts.get(cat, 0))
        pct = round((count / len(df)) * 100, 2) if len(df) > 0 else 0.0
        
        # Get 3 representative raw feedback text examples (with high confidence, sorted descending)
        cat_df = df[df['ai_category'] == cat]
        cat_df_sorted = cat_df.sort_values('ai_confidence', ascending=False)
        examples = cat_df_sorted['feedback_text'].head(3).tolist()
        
        category_dist[cat] = {
            'Count': count,
            'Percentage': pct,
            'Examples': examples
        }
    results['category'] = category_dist
    
    # Sentiment
    sent_counts = df['ai_sentiment'].value_counts()
    results['sentiment'] = pd.DataFrame({
        'Count': sent_counts,
        'Percentage': (sent_counts / len(df)) * 100
    }).round(2).to_dict(orient='index')
    
    # Source
    src_counts = df['source'].value_counts()
    results['source'] = pd.DataFrame({
        'Count': src_counts,
        'Percentage': (src_counts / len(df)) * 100
    }).round(2).to_dict(orient='index')
    
    return results

def compute_crosstabs(df):
    """
    Computes cross-tabulations between source/category and source/sentiment.
    """
    source_vs_cat = pd.crosstab(df['source'], df['ai_category'], normalize='index') * 100
    source_vs_sent = pd.crosstab(df['source'], df['ai_sentiment'], normalize='index') * 100
    
    return {
        "source_vs_category": source_vs_cat.round(2).to_dict(orient='index'),
        "source_vs_sentiment": source_vs_sent.round(2).to_dict(orient='index')
    }

def analyze_rating_sentiment_conflicts(df):
    """
    Identifies records where the numerical rating contradicts the AI sentiment.
    - Rating >= 4 and Sentiment = Negative (Sarcasm/user click error)
    - Rating <= 2 and Sentiment = Positive (User support praise but low rating or visa-versa)
    """
    if len(df) == 0:
        return {"conflict_count": 0, "conflict_percentage": 0.0}
        
    conflicts = df[
        ((df['rating'] >= 4) & (df['ai_sentiment'] == 'Negative')) |
        ((df['rating'] <= 2) & (df['ai_sentiment'] == 'Positive'))
    ]
    
    conflict_count = len(conflicts)
    conflict_percentage = (conflict_count / len(df)) * 100
    
    return {
        "conflict_count": conflict_count,
        "conflict_percentage": round(conflict_percentage, 2),
        "conflicts_sample": conflicts[['id', 'rating', 'ai_sentiment', 'feedback_text']].head(5).to_dict(orient='records')
    }

def analyze_trends(df):
    """
    Performs trend analysis on weekly intervals.
    Determines if customer sentiment is improving or worsening.
    """
    # Filter out records without valid timestamps
    df_trends = df[df['timestamp'].notna()].copy()
    if len(df_trends) == 0:
        return {
            "status": "Stable",
            "reason": "Insufficient timestamp data to compute trend.",
            "weekly_data": []
        }
        
    df_trends['timestamp'] = pd.to_datetime(df_trends['timestamp'])
    df_trends = df_trends.sort_values('timestamp')
    
    # Resample weekly and compute metrics
    df_trends.set_index('timestamp', inplace=True)
    weekly = df_trends.resample('W')
    
    weekly_records = []
    for name, group in weekly:
        if len(group) == 0:
            continue
        total_count = len(group)
        neg_count = (group['ai_sentiment'] == 'Negative').sum()
        neg_pct = (neg_count / total_count) * 100
        
        weekly_records.append({
            "week_start": name.strftime('%Y-%m-%d'),
            "total_complaints": int(total_count),
            "negative_sentiment_percentage": round(neg_pct, 2)
        })
        
    if len(weekly_records) < 2:
        return {
            "status": "Stable",
            "reason": "Not enough weekly data points to calculate direction.",
            "weekly_data": weekly_records
        }
        
    # Analyze direction (slope of negative sentiment)
    # Compare first 30% of weeks to last 30% of weeks
    split_idx = max(1, len(weekly_records) // 3)
    start_weeks = weekly_records[:split_idx]
    end_weeks = weekly_records[-split_idx:]
    
    start_neg_avg = np.mean([w['negative_sentiment_percentage'] for w in start_weeks])
    end_neg_avg = np.mean([w['negative_sentiment_percentage'] for w in end_weeks])
    
    diff = end_neg_avg - start_neg_avg
    
    if diff < -2.0:
        status = "Improving"
        reason = f"Negative sentiment decreased from {round(start_neg_avg, 1)}% to {round(end_neg_avg, 1)}% during the observed period."
    elif diff > 2.0:
        status = "Worsening"
        reason = f"Negative sentiment increased from {round(start_neg_avg, 1)}% to {round(end_neg_avg, 1)}% during the observed period."
    else:
        status = "Stable"
        reason = f"Negative sentiment remained stable (changed from {round(start_neg_avg, 1)}% to {round(end_neg_avg, 1)}%)."
        
    return {
        "status": status,
        "reason": reason,
        "weekly_data": weekly_records
    }

def generate_recommendations(df, distributions, conflicts, trends):
    """
    Generates actionable business recommendations based on the findings.
    """
    recs = []
    
    # 1. Category-specific recommendations
    cat_dist = distributions['category']
    delivery_pct = cat_dist.get('Delivery', {}).get('Percentage', 0.0)
    app_pct = cat_dist.get('App Bug', {}).get('Percentage', 0.0)
    billing_pct = cat_dist.get('Billing', {}).get('Percentage', 0.0)
    support_pct = cat_dist.get('Staff/Support', {}).get('Percentage', 0.0)
    
    # Delivery priority
    if delivery_pct > 30.0:
        recs.append({
            "title": "Perform Logistics Partner Audit & SLA Review",
            "impact": "High",
            "description": f"Delivery issues account for {delivery_pct}% of customer complaints. Management should audit third-party logistics partners, penalize delayed drops, and establish strict packaging guidelines to prevent food spills."
        })
        
    # App bug priority
    if app_pct > 25.0:
        recs.append({
            "title": "Mobile App Crash & Checkout Bug Fix",
            "impact": "High",
            "description": f"App bugs represent {app_pct}% of complaints. Engineering teams must prioritize solving the checkout screen freezes, payment gateway failures, and address-saving issues reported in the latest app release."
        })
        
    # Billing priority
    if billing_pct > 15.0:
        recs.append({
            "title": "Audit Coupon Application & Double Charges",
            "impact": "Medium",
            "description": f"Billing anomalies affect {billing_pct}% of complaints. System audits are required for the SAVE50 coupon application mechanics during checkout, and a payment refund program must reverse double-deductions promptly."
        })
        
    # Support priority
    if support_pct > 15.0:
        recs.append({
            "title": "Retrain Support Staff and Implement Escalation Rules",
            "impact": "Medium",
            "description": f"Support issues represent {support_pct}% of tickets. Improve support response SLAs (currently customers report long hold times) and train agents to avoid boilerplate/copy-paste replies for urgent refund issues."
        })
        
    # 2. Trend-specific recommendation
    trend_status = trends['status']
    if trend_status == "Worsening":
        recs.append({
            "title": "Urgent Service Recovery Program",
            "impact": "Critical",
            "description": "Customer sentiment is worsening over time, with negative complaints rising. Form an immediate service recovery team to contact high-value clients who reported negative delivery and billing experiences."
        })
    elif trend_status == "Stable":
        recs.append({
            "title": "Establish Feedback Loops for Category Hotspots",
            "impact": "Low",
            "description": "Sentiment is stable but complaints remain constant. Focus on solving the top category drivers sequentially to shift sentiment positive."
        })
        
    # 3. Conflict / Sarcasm recommendation
    conflict_pct = conflicts['conflict_percentage']
    if conflict_pct > 8.0:
        recs.append({
            "title": "Review Feedback Rating UI & Sarcasm Filters",
            "impact": "Low",
            "description": f"A high contradiction rate ({conflict_pct}%) exists between customer ratings and text reviews. UI design should test if users are misclicking star ratings, and the customer success dashboard should use text analysis to flag complaints instead of relying solely on star-based alerts."
        })
        
    # If no criteria match, provide generic smart recommendations
    if not recs:
        recs.append({
            "title": "Monitor App Release Performance",
            "impact": "Medium",
            "description": "Maintain regular weekly monitoring of category complaints. App release updates should be gated by regression testing of payment and map screen elements."
        })
        
    # Sort recommendations by impact severity
    impact_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    recs = sorted(recs, key=lambda x: impact_order.get(x['impact'], 4))
    
    return recs
