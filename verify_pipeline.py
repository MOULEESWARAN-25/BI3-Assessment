"""
verify_pipeline.py — Developer CLI tool to verify the full pipeline.

Usage:
    python verify_pipeline.py <path_to_csv_or_excel>

Example:
    python verify_pipeline.py sample_data.csv
"""
import sys
import os
import pandas as pd

from src.audit import audit_dataset
from src.cleaning import clean_dataset, normalize_text_for_dedup
from src.llm import analyze_feedback, get_api_status, reset_api_circuit
from src.enrichment import enrich_dataset
from src.validation import validate_and_correct_dataset
from src.insights import (
    compute_distributions,
    compute_crosstabs,
    analyze_rating_sentiment_conflicts,
    analyze_trends,
    generate_recommendations
)
from src.report_generator import generate_markdown_report, generate_html_report


def run_verification(file_path: str):
    reset_api_circuit()
    print("==================================================")
    print("QuickCart Customer Feedback Pipeline Verification")
    print("==================================================")

    # 1. Load Data (from provided path only — no fallback to hardcoded local files)
    if not os.path.exists(file_path):
        print(f"Error: File not found: '{file_path}'")
        print("Usage: python verify_pipeline.py <path_to_csv_or_excel>")
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        df_raw = pd.read_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        df_raw = pd.read_excel(file_path)
    else:
        print(f"Error: Unsupported file type '{ext}'. Please provide a .csv or .xlsx file.")
        sys.exit(1)

    print(f"Loaded '{file_path}' with {len(df_raw)} records.")

    # 2. Run Audit
    print("\n--- 1. Executing Data Quality Audit ---")
    audit_res = audit_dataset(df_raw)
    print(f"Dataset Health Score:                   {audit_res['health_score']}/100")
    print(f"Missing Timestamps:                     {audit_res['missing_timestamp_count']}")
    print(f"Missing Ratings:                        {audit_res['missing_rating_count']}")
    print(f"Exact Duplicate Rows:                   {audit_res['duplicate_row_count']}")
    print(f"Duplicate Feedback Text:                {audit_res['duplicate_feedback_count']}")
    print(f"Empty/Meaningless Feedback:             {audit_res['empty_feedback_count']}")
    print(f"Invalid Timestamps:                     {audit_res['invalid_timestamp_count']}")
    print(f"Potential Rating/Sentiment Conflicts:   {audit_res['contradiction_count']}")
    print(f"Agent name mentions:                    {audit_res['agent_mentions_count']}")
    print(f"Order number mentions:                  {audit_res['order_number_count']}")
    print(f"Multilingual comments:                  {audit_res['multilingual_count']}")

    # 3. Text Normalization Samples
    print("\n--- 2. Testing Text Normalization ---")
    sample_texts = [
        "Coupon SAVE50 failed during checkout. (order #409153)",
        "COUPON SAVE50 failed during checkout. - my sushi order in Bangalore",
        "Coupon SAVE50 failed during checkout. Agent Priya was handling it.!!!!",
        "Items were missing from my delivery, got only half the order (order #133795) This is the third time."
    ]
    for txt in sample_texts:
        norm = normalize_text_for_dedup(txt)
        print(f"Original:   {txt}")
        print(f"Normalized: {norm}\n")

    # 4. Cleaning
    print("\n--- 3. Running Data Cleaning ---")
    cleaned_df, cleaning_log = clean_dataset(df_raw)
    print(f"Valid records retained:     {len(cleaned_df)}")
    print(f"Empty/meaningless removed:  {cleaning_log['empty_removed']}")
    print(f"Exact duplicates removed:   {cleaning_log['exact_duplicates_removed']}")
    print(f"Near-duplicates flagged:    {cleaning_log['normalized_duplicates_removed']}")
    print(f"Timestamps standardized:    {cleaning_log['timestamps_standardized']}")

    # 5. Local Heuristic Classifier
    print("\n--- 4. Testing Local Heuristic Classifier (Offline Mode) ---")
    api_status = get_api_status()
    print(f"Active Provider: {api_status['status']} ({api_status['model']})")

    test_cases = [
        ("Driver was rude and threw the bag on the floor", 1),
        ("Refund hasn't arrived after 10 days, charging me twice!", 5),  # Sarcasm
        ("App crashed on loading screen", 2),
        ("Priya solved my issue quickly", 5),
        ("Mera refund abhi tak nahi aaya, bahut bura service hai", 1),   # Hinglish Billing
        ("Random question, who designed your logo", None)                 # Other
    ]
    for txt, rating in test_cases:
        res = analyze_feedback(txt, rating)
        print(f"Text: '{txt}' | Rating: {rating}")
        print(f"  -> Sentiment={res.get('sentiment')}, Category={res.get('category')}, "
              f"Summary='{res.get('summary')}', Confidence={res.get('confidence')}\n")

    # 6. Enrichment (all records)
    print("\n--- 5. Running Full Enrichment & Validation ---")
    def report_progress(count, total):
        print(f"  Processed {count}/{total} records...", end="\r")
    full_enriched = enrich_dataset(cleaned_df, progress_callback=report_progress)
    print(f"\nEnrichment complete: {len(full_enriched)} records enriched.")

    # Inject deliberate errors to test the validation layer
    full_enriched.loc[0, 'ai_category'] = "Payment Issue"     # invalid category
    full_enriched.loc[1, 'ai_sentiment'] = "Slightly Negative" # invalid sentiment

    full_validated, corrections, full_metrics = validate_and_correct_dataset(
        full_enriched, health_score=audit_res['health_score']
    )
    print(f"Validation corrections applied: {len(corrections)}")
    for corr in corrections:
        print(f"  Record {corr['record_id']} | {corr['field']}: "
              f"'{corr['original_value']}' -> '{corr['corrected_value']}' ({corr['reason']})")
    print(f"\nAverage AI Confidence:  {full_metrics['average_confidence'] * 100:.1f}%")
    print(f"Insight Reliability:    {full_metrics['insight_reliability']}")

    # 7. Insights
    print("\n--- 6. Generating Insights ---")
    distributions = compute_distributions(full_validated)
    crosstabs = compute_crosstabs(full_validated)
    conflicts = analyze_rating_sentiment_conflicts(full_validated)
    trends = analyze_trends(full_validated)
    recommendations = generate_recommendations(full_validated, distributions, conflicts, trends)

    print(f"Contradiction Rate:  {conflicts['conflict_percentage']}%")
    print(f"Trend Direction:     {trends['status']}")
    print(f"Trend Details:       {trends['reason']}")
    print("\nTop Complaint Categories:")
    for cat, data in distributions['category'].items():
        print(f"  {cat}: {data['Count']} cases ({data['Percentage']}%)")
    print("\nBusiness Recommendations Generated:")
    for idx, rec in enumerate(recommendations):
        print(f"  {idx+1}. [{rec['impact']} Impact] {rec['title']}")
        print(f"     {rec['description']}")

    # 8. Report Generation (in-memory only — no files written to disk)
    print("\n--- 7. Generating Reports (in-memory) ---")
    md_report = generate_markdown_report(
        audit_res, cleaning_log, full_metrics, distributions, conflicts, trends, recommendations
    )
    html_report = generate_html_report(
        audit_res, cleaning_log, full_metrics, distributions, conflicts, trends, recommendations
    )
    print(f"Markdown report size:  {len(md_report):,} characters")
    print(f"HTML report size:      {len(html_report):,} characters")

    print("\n==================================================")
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_pipeline.py <path_to_csv_or_excel>")
        print("Example: python verify_pipeline.py sample_data.csv")
        sys.exit(1)
    run_verification(sys.argv[1])
