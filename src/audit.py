import re
import pandas as pd
import numpy as np
from dateutil import parser  # type: ignore[import-untyped]
from src import config

def is_empty_or_meaningless(text):
    """
    Checks if the feedback text is missing, empty, or consists only of meaningless text or placeholders.
    """
    if pd.isna(text) or not isinstance(text, str):
        return True
    
    text_stripped = text.strip()
    if not text_stripped:
        return True
    
    # 1. Very short texts (e.g. "meh", "ok", "👍", "???", "ok i guess")
    if len(text_stripped) < 4:
        return True
    
    # Check for placeholder phrases (case insensitive)
    placeholders = ['ok i guess', 'meh', 'ignore', 'test test test ignore', 'test test', 'ok guess', 'ignoring']
    if text_stripped.lower() in placeholders:
        return True
        
    # 2. Check for only punctuation or symbols (e.g. "....", "????", "😡😡😡😡")
    # Clean letters and numbers
    alphanumeric = re.sub(r'[^a-zA-Z0-9]', '', text_stripped)
    if len(alphanumeric) == 0:
        return True
        
    # 3. Check for repeating single characters (e.g., "aaaaaaaaaaaaaaa")
    if len(set(text_stripped.lower())) == 1 and len(text_stripped) > 3:
        return True
        
    return False

def try_parse_date(val):
    """
    Tries to parse the timestamp value. Returns the parsed datetime object, or None if invalid/empty.
    """
    if pd.isna(val) or not isinstance(val, str) or not val.strip():
        return None
    
    val_clean = val.strip().strip('"').strip("'")
    
    # Simple format checks to handle known traps
    try:
        # Check standard dateutil parsing
        parsed = parser.parse(val_clean, fuzzy=False)
        return parsed
    except Exception:
        # Fallback manual parsing for custom formats if dateutil fails
        formats = [
            "%d-%b-%y",      # 02-Feb-24
            "%m/%d/%Y",      # 02/14/2024
            "%d/%m/%Y",      # 28/02/2024
            "%Y-%m-%d %H:%M:%S", # 2024-03-25 16:31:48
            "%B %d, %Y",     # March 18, 2024
            "%b %d %Y",      # Jan 18 2024
            "%Y-%m-%d"       # 2024-03-25
        ]
        for fmt in formats:
            try:
                from datetime import datetime
                return datetime.strptime(val_clean, fmt)
            except ValueError:
                continue
    return None

def detect_potential_contradiction(row):
    """
    Heuristically detects contradictions between ratings and feedback text sentiment.
    """
    rating = row.get('rating')
    text = row.get('feedback_text')
    
    if pd.isna(rating) or pd.isna(text) or not isinstance(text, str):
        return False
    
    try:
        rating = float(rating)
    except (ValueError, TypeError):
        return False
    text_lower = text.lower()
    
    # Positive triggers
    positive_words = ['great', 'love', 'fantastic', 'wonderful', 'perfect', 'helpful', 'solved', 'excellent']
    # Negative triggers
    negative_words = ['failed', 'crash', 'charge', 'deduct', 'spill', 'rude', 'late', 'cancel', 'error', 'worst', 'ridiculous', 'double']
    
    has_positive = any(word in text_lower for word in positive_words)
    has_negative = any(word in text_lower for word in negative_words)
    
    # Rating 5 or 4 with negative keywords (e.g. "crashed again, just love it" - sarcasm)
    if rating >= 4.0 and has_negative and not has_positive:
        return True
    
    # Rating 1 or 2 with positive keywords (e.g. "Priya solved it well" but rated 1)
    if rating <= 2.0 and has_positive and not has_negative:
        return True
        
    return False

def audit_dataset(df):
    """
    Performs a full audit of the raw dataset.
    Returns a dictionary of metrics.
    """
    total_records = len(df)
    if total_records == 0:
        return {
            "total_records": 0,
            "health_score": 100,
            "missing_timestamp_count": 0,
            "missing_rating_count": 0,
            "duplicate_row_count": 0,
            "duplicate_feedback_count": 0,
            "empty_feedback_count": 0,
            "invalid_timestamp_count": 0,
            "contradiction_count": 0,
            "agent_mentions_count": 0,
            "order_number_count": 0,
            "multilingual_count": 0
        }
    
    # 1. Missing Timestamps
    missing_timestamp_count = df['timestamp'].isna().sum() + df['timestamp'].apply(lambda x: str(x).strip() == '' if pd.notna(x) else False).sum()
    
    # 2. Missing Ratings
    missing_rating_count = df['rating'].isna().sum()
    
    # 3. Duplicate Rows (exact across all fields)
    duplicate_row_count = df.duplicated().sum()
    
    # 4. Duplicate Feedbacks (raw text match)
    duplicate_feedback_count = df['feedback_text'].duplicated().sum()
    
    # 5. Empty / Meaningless Feedback
    empty_feedback_count = df['feedback_text'].apply(is_empty_or_meaningless).sum()
    
    # 6. Invalid Timestamps (present but unparseable)
    def check_invalid_ts(val):
        if pd.isna(val) or str(val).strip() == '':
            return False # Count as missing, not invalid
        parsed = try_parse_date(str(val))
        return parsed is None

    invalid_timestamp_count = df['timestamp'].apply(check_invalid_ts).sum()
    
    # 7. Potential Rating/Text contradictions
    contradiction_count = df.apply(detect_potential_contradiction, axis=1).sum()
    
    # 8. Additional Anomalies
    # Agent mentions
    agent_pattern = re.compile(r'agent\s+(priya|meera|vikram|rahul|sana|anil|neha|arjun|moulee)', re.IGNORECASE)
    agent_mentions_count = df['feedback_text'].apply(
        lambda x: bool(agent_pattern.search(str(x))) if pd.notna(x) else False
    ).sum()
    
    # Order numbers
    order_pattern = re.compile(r'order\s*#\s*\d+', re.IGNORECASE)
    order_number_count = df['feedback_text'].apply(
        lambda x: bool(order_pattern.search(str(x))) if pd.notna(x) else False
    ).sum()
    
    # Multilingual/Foreign language indicators
    foreign_words = ['pedido', 'llego', 'tarde', 'livreur', 'impoli', 'cierra', 'aplicacion', 'mera', 'aaya', 'bura', 'accci', 'nahi']
    def check_multilingual(text):
        if pd.isna(text) or not isinstance(text, str):
            return False
        text_lower = text.lower()
        return any(word in text_lower for word in foreign_words)
    
    multilingual_count = df['feedback_text'].apply(check_multilingual).sum()
    
    # Calculate Dataset Health Score (Base 100, deduct penalty per % of total records)
    deductions = (
        (missing_timestamp_count / total_records) * 100 * config.HEALTH_PENALTY_MISSING_TIMESTAMP +
        (missing_rating_count / total_records) * 100 * config.HEALTH_PENALTY_MISSING_RATING +
        (duplicate_row_count / total_records) * 100 * config.HEALTH_PENALTY_DUPLICATE_ROW +
        (duplicate_feedback_count / total_records) * 100 * config.HEALTH_PENALTY_DUPLICATE_FEEDBACK +
        (empty_feedback_count / total_records) * 100 * config.HEALTH_PENALTY_EMPTY_FEEDBACK +
        (invalid_timestamp_count / total_records) * 100 * config.HEALTH_PENALTY_INVALID_TIMESTAMP
    )
    
    health_score = max(0, min(100, int(100 - deductions)))
    
    return {
        "total_records": total_records,
        "health_score": health_score,
        "missing_timestamp_count": int(missing_timestamp_count),
        "missing_rating_count": int(missing_rating_count),
        "duplicate_row_count": int(duplicate_row_count),
        "duplicate_feedback_count": int(duplicate_feedback_count),
        "empty_feedback_count": int(empty_feedback_count),
        "invalid_timestamp_count": int(invalid_timestamp_count),
        "contradiction_count": int(contradiction_count),
        "agent_mentions_count": int(agent_mentions_count),
        "order_number_count": int(order_number_count),
        "multilingual_count": int(multilingual_count)
    }
