import re
import pandas as pd
import numpy as np
from src.audit import try_parse_date, is_empty_or_meaningless

def clean_feedback_text(text):
    """
    Cleans feedback text by trimming and collapsing whitespace, but keeps original text structure.
    """
    if pd.isna(text) or not isinstance(text, str):
        return ""
    # Collapse double spaces
    cleaned = re.sub(r'\s+', ' ', text.strip())
    return cleaned

def normalize_text_for_dedup(text):
    """
    Normalizes feedback text for deduplication. Strips order IDs, agent mentions,
    city suffixes, and formatting noise to detect identical underlying complaints.
    """
    if pd.isna(text) or not isinstance(text, str):
        return ""
    
    # Lowercase
    normalized = text.lower().strip()
    
    # 1. Strip agent mentions (e.g., "Agent Priya was handling it.!!!!")
    agent_pattern = r"\bagent\s+\w+\s+was\s+handling\s+it[\s\.!]*"
    normalized = re.sub(agent_pattern, "", normalized, flags=re.IGNORECASE)
    
    # 2. Strip "Thank you to the agent Priya who handled my complaint so well" boilerplate
    agent_thank_you_pattern = r"thank\s+you\s+to\s+the\s+agent\s+\w+\s+who\s+handled\s+my\s+complaint\s+so\s+well[\s\(\)#\d]*"
    normalized = re.sub(agent_thank_you_pattern, "", normalized, flags=re.IGNORECASE)
    
    # 3. Strip order numbers (e.g. "(order #12345)")
    order_pattern_1 = r"\(\s*order\s*#\s*\d+\s*\)"
    order_pattern_2 = r"\border\s*#\s*\d+\b"
    normalized = re.sub(order_pattern_1, "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(order_pattern_2, "", normalized, flags=re.IGNORECASE)
    
    # 4. Strip city suffixes (e.g., "- my thali order in Chennai" or "- my groceries order in Pune")
    city_suffix_pattern = r"-\s*my\s+[\w\s]+\s+order\s+in\s+\w+"
    normalized = re.sub(city_suffix_pattern, "", normalized, flags=re.IGNORECASE)
    
    # 5. Strip "This is the X time" tags
    repetition_pattern = r"\bthis\s+is\s+the\s+(first|second|third|fourth|fifth|last)\s+time[\s\.!]*"
    normalized = re.sub(repetition_pattern, "", normalized, flags=re.IGNORECASE)
    
    # 6. Clean repeating punctuation and symbols
    normalized = re.sub(r'!+', '!', normalized)
    normalized = re.sub(r'\.+', '.', normalized)
    normalized = re.sub(r'\?+', '?', normalized)
    
    # Collapse multiple spaces again
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # If normalized result is empty, fallback to the cleaned original text in lowercase
    if not normalized:
        normalized = text.lower().strip()
        
    return normalized

def impute_rating(row):
    rating = row.get('rating')
    if pd.notna(rating):
        try:
            return float(rating)
        except ValueError:
            pass
    # Impute based on text sentiment words
    text = str(row.get('feedback_text', '')).lower()
    pos_words = ['great', 'love', 'perfect', 'fantastic', 'good', 'thanks', 'excelente', 'friendly', 'solved']
    neg_words = ['crash', 'fail', 'cancel', 'refund', 'worst', 'late', 'bad', 'rude', 'charge', 'double', 'spill']
    if any(w in text for w in neg_words):
        return 1.0
    elif any(w in text for w in pos_words):
        return 5.0
    return 3.0

def clean_dataset(df):
    """
    Runs the full cleaning pipeline.
    Returns:
      - cleaned_df: The cleaned pandas DataFrame.
      - decisions_log: A dictionary summarizing the cleaning numbers and decisions.
    """
    total_raw = len(df)
    decisions_log = {
        "total_raw": total_raw,
        "empty_removed": 0,
        "exact_duplicates_removed": 0,
        "normalized_duplicates_removed": 0,
        "timestamps_standardized": 0,
        "unparseable_timestamps_kept": 0,
        "total_cleaned_saved": 0
    }
    
    if total_raw == 0:
        return df.copy(), decisions_log

    working_df = df.copy()
    if 'id' not in working_df.columns:
        working_df['id'] = range(1, len(working_df) + 1)
    
    # 1. Remove empty/meaningless feedback
    is_empty_mask = working_df['feedback_text'].apply(is_empty_or_meaningless)
    decisions_log["empty_removed"] = int(is_empty_mask.sum())
    working_df = working_df[~is_empty_mask]
    
    # 2. Trim whitespace on text
    working_df['feedback_text'] = working_df['feedback_text'].apply(clean_feedback_text)
    
    # 3. Standardize and Impute timestamps to ISO YYYY-MM-DD
    standardized_dates = []
    standardized_count = 0
    unparseable_count = 0
    
    for ts in working_df['timestamp']:
        parsed_dt = try_parse_date(str(ts) if pd.notna(ts) else "")
        if parsed_dt:
            standardized_dates.append(parsed_dt.strftime('%Y-%m-%d'))
            standardized_count += 1
        else:
            standardized_dates.append(None)
            unparseable_count += 1
            
    working_df['timestamp'] = standardized_dates
    # Forward-fill and backward-fill missing timestamps to resolve nulls chronologically
    working_df['timestamp'] = working_df['timestamp'].ffill().bfill()
    
    decisions_log["timestamps_standardized"] = standardized_count
    decisions_log["unparseable_timestamps_kept"] = 0
    
    # 4. Impute missing/null ratings based on feedback text
    working_df['rating'] = working_df.apply(impute_rating, axis=1)
    
    # 5. Remove exact duplicates across all rows (if any)
    initial_len = len(working_df)
    working_df = working_df.drop_duplicates()
    decisions_log["exact_duplicates_removed"] = int(initial_len - len(working_df))
    
    # 6. Detect near-duplicates after text normalization (but do NOT drop them)
    # Add a normalized column for deduplication check
    working_df['normalized_text'] = working_df['feedback_text'].apply(normalize_text_for_dedup)
    
    # Keep track of counts of normalized duplicates to preserve frequency metrics
    norm_counts = working_df['normalized_text'].value_counts()
    working_df['complaint_count'] = working_df['normalized_text'].map(norm_counts)
    
    cleaned_df = working_df.copy()
    decisions_log["normalized_duplicates_removed"] = 0
    decisions_log["total_cleaned_saved"] = len(cleaned_df)
    
    # Reindex columns cleanly
    cleaned_df = cleaned_df[['id', 'timestamp', 'source', 'rating', 'feedback_text', 'normalized_text', 'complaint_count']]
    
    return cleaned_df, decisions_log
