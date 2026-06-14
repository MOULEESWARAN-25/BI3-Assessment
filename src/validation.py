import pandas as pd
from src import config

def calculate_insight_reliability(health_score, average_confidence):
    """
    Computes an Insight Reliability classification (High, Medium, Limited by Source Data Quality)
    based on the dataset health score and average AI confidence.
    """
    if health_score >= 80 and average_confidence >= 0.85:
        return "High"
    elif health_score < 60 or average_confidence < 0.70:
        return "Limited by Source Data Quality"
    else:
        return "Medium"

def validate_and_correct_dataset(enriched_df, health_score=80):
    """
    Runs strict checks on AI output, maps invalid values to standard enums,
    flags low confidence records, and logs corrections in a simplified JSON format.
    
    Returns:
      validated_df: The DataFrame with corrected fields.
      corrections_log: A list of dicts summarizing corrections applied.
      summary_metrics: Dict containing average confidence, low confidence count, and reliability.
    """
    validated_df = enriched_df.copy()
    corrections_log = []
    
    low_confidence_count = 0
    
    for idx, row in validated_df.iterrows():
        record_id = int(row['id'])
        orig_sentiment = row['ai_sentiment']
        orig_category = row['ai_category']
        confidence = float(row['ai_confidence'])
        
        # Track low confidence
        if confidence < 0.70:
            low_confidence_count += 1
            
        corrected_sentiment = orig_sentiment
        corrected_category = orig_category
        
        # 1. VALIDATE SENTIMENT
        if orig_sentiment not in config.ALLOWED_SENTIMENTS:
            sentiment_clean = str(orig_sentiment).lower().strip()
            if any(x in sentiment_clean for x in ['neg', 'bad', 'poor']):
                corrected_sentiment = "Negative"
            elif any(x in sentiment_clean for x in ['pos', 'good', 'great', 'star']):
                corrected_sentiment = "Positive"
            else:
                corrected_sentiment = "Neutral"
                
            corrections_log.append({
                "record_id": record_id,
                "field": "sentiment",
                "original_value": orig_sentiment,
                "corrected_value": corrected_sentiment,
                "reason": f"Value '{orig_sentiment}' mapped to standard sentiment '{corrected_sentiment}'"
            })
            
        # 2. VALIDATE CATEGORY
        if orig_category not in config.ALLOWED_CATEGORIES:
            category_clean = str(orig_category).lower().strip()
            # Try matching lookup config map
            matched = False
            for kw, allowed_cat in config.CATEGORY_FALLBACK_MAP.items():
                if kw in category_clean:
                    corrected_category = allowed_cat
                    matched = True
                    break
            
            if not matched:
                # If still not matched, fallback to scan words in feedback text
                text_clean = str(row['feedback_text']).lower()
                for cat_allowed, keywords in config.MOCK_CATEGORY_RULES.items():
                    if any(kw in text_clean for kw in keywords):
                        corrected_category = cat_allowed
                        matched = True
                        break
            
            if not matched:
                corrected_category = "Other"
                
            corrections_log.append({
                "record_id": record_id,
                "field": "category",
                "original_value": orig_category,
                "corrected_value": corrected_category,
                "reason": f"Value '{orig_category}' mapped to standard category '{corrected_category}'"
            })
            
        # Apply corrections back to DataFrame
        validated_df.at[idx, 'ai_sentiment'] = corrected_sentiment
        validated_df.at[idx, 'ai_category'] = corrected_category
        
    # Mark needs_human_review
    validated_df['needs_human_review'] = validated_df['ai_confidence'].apply(lambda x: x < 0.70)
    
    # Calculate metrics
    avg_confidence = float(validated_df['ai_confidence'].mean()) if len(validated_df) > 0 else 1.0
    reliability = calculate_insight_reliability(health_score, avg_confidence)
    
    summary_metrics = {
        "average_confidence": round(avg_confidence, 4),
        "low_confidence_count": low_confidence_count,
        "low_confidence_percentage": round((low_confidence_count / len(validated_df)) * 100, 2) if len(validated_df) > 0 else 0.0,
        "insight_reliability": reliability
    }
    
    return validated_df, corrections_log, summary_metrics
