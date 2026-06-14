import pandas as pd
from src.llm import analyze_feedback_batch

def enrich_dataset(cleaned_df, progress_callback=None):
    """
    Takes the cleaned dataset and enriches it using the AI layer in batches.
    Optimized to query the LLM only for unique feedback_text, mapping the results
    back to all matching entries to keep the full dataset intact efficiently.
    """
    if len(cleaned_df) == 0:
        return cleaned_df.copy()
        
    # Get unique normalized_text rows to minimize LLM queries
    unique_df = cleaned_df.drop_duplicates(subset=['normalized_text']).copy()
    unique_total = len(unique_df)
    
    # Assign a temporary unique ID for mapping batch results back
    unique_df['temp_unique_id'] = range(unique_total)
    
    records_to_process = []
    for _, row in unique_df.iterrows():
        records_to_process.append({
            'id': int(row['temp_unique_id']),
            'feedback_text': row['feedback_text'],
            'rating': row['rating'],
            'timestamp': row['timestamp'],
            'source': row['source'],
            'normalized_text': row['normalized_text'],
            'complaint_count': row['complaint_count']
        })
        
    batch_size = 20
    enriched_unique = []
    
    for i in range(0, unique_total, batch_size):
        batch = records_to_process[i:i+batch_size]
        batch_results = analyze_feedback_batch(batch)
        enriched_unique.extend(batch_results)
        
        if progress_callback:
            progress_callback(min(i + batch_size, unique_total), unique_total)
            
    # Create a mapping dictionary from normalized_text -> AI results
    mapping = {}
    for res in enriched_unique:
        matching_row = unique_df[unique_df['temp_unique_id'] == res['id']]
        if not matching_row.empty:
            norm_txt = matching_row.iloc[0]['normalized_text']
            mapping[norm_txt] = {
                'ai_sentiment': res.get('ai_sentiment', 'Neutral'),
                'ai_category': res.get('ai_category', 'Other'),
                'ai_summary': res.get('ai_summary', norm_txt[:50]),
                'ai_confidence': res.get('ai_confidence', 0.8)
            }
            
    # Expand the results back to the original rows in cleaned_df
    full_enriched_records = []
    for _, row in cleaned_df.iterrows():
        norm_txt = row['normalized_text']
        ai_res = mapping.get(norm_txt, {
            'ai_sentiment': 'Neutral',
            'ai_category': 'Other',
            'ai_summary': row['feedback_text'][:50],
            'ai_confidence': 0.8
        })
        
        full_enriched_records.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'source': row['source'],
            'rating': row['rating'],
            'feedback_text': row['feedback_text'],
            'normalized_text': row['normalized_text'],
            'complaint_count': row['complaint_count'],
            'ai_sentiment': ai_res['ai_sentiment'],
            'ai_category': ai_res['ai_category'],
            'ai_summary': ai_res['ai_summary'],
            'ai_confidence': ai_res['ai_confidence']
        })
        
    enriched_df = pd.DataFrame(full_enriched_records)
    return enriched_df
