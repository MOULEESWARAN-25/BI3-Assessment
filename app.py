import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import time

from src.audit import audit_dataset
from src.cleaning import clean_dataset
from src.llm import get_api_status, reset_api_circuit
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
from src import config

# Page configuration
st.set_page_config(
    page_title="QuickCart Feedback Intelligence Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern styling via CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
        letter-spacing: -0.03em;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #64748b;
        margin-bottom: 28px;
        font-weight: 500;
        letter-spacing: -0.01em;
    }
    
    /* Premium KPI Card styling */
    .kpi-container {
        display: flex;
        gap: 16px;
        margin-bottom: 16px;
    }
    
    .kpi-card {
        flex: 1;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 24px 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.02), 0 4px 6px -4px rgba(0, 0, 0, 0.02), inset 0 2px 4px 0 rgba(255,255,255,0.8);
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: transparent;
        transition: background-color 0.3s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
        border-color: #cbd5e1;
    }
    
    .kpi-card:hover::before {
        background: linear-gradient(90deg, #3b82f6, #7c3aed);
    }
    
    .kpi-header {
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 10px;
    }
    
    .kpi-value {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
    }
    
    .kpi-highlight-blue { color: #2563eb; }
    .kpi-highlight-green { color: #10b981; }
    .kpi-highlight-orange { color: #f59e0b; }
    .kpi-highlight-red { color: #ef4444; }
    
    .reliability-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 2px 4px 0 rgba(0,0,0,0.02);
    }
    .rel-high { background-color: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
    .rel-medium { background-color: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
    .rel-low { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fca5a5; }
    .rel-limited-by-source-data-quality { background-color: #fef2f2; color: #b91c1c; font-size: 0.725rem !important; border: 1px solid #fca5a5; }
    
    /* Recommendations styling */
    .rec-card {
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 18px;
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 6px solid #64748b;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -2px rgba(0, 0, 0, 0.02);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .rec-card:hover {
        transform: translateX(6px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.04), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
        border-color: #cbd5e1;
    }
    
    .rec-critical { border-left-color: #ef4444; background: linear-gradient(90deg, #fef2f2 0%, #ffffff 100%); }
    .rec-high { border-left-color: #f59e0b; background: linear-gradient(90deg, #fffbeb 0%, #ffffff 100%); }
    .rec-medium { border-left-color: #3b82f6; background: linear-gradient(90deg, #eff6ff 0%, #ffffff 100%); }
    .rec-low { border-left-color: #10b981; background: linear-gradient(90deg, #f0fdf4 0%, #ffffff 100%); }
    
    .rec-title {
        font-weight: 800;
        font-size: 1.1rem;
        color: #0f172a;
        margin-bottom: 6px;
        letter-spacing: -0.015em;
    }
    
    .rec-meta {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748b;
        margin-bottom: 10px;
        letter-spacing: 0.05em;
    }
    
    /* Pipeline Step visualizer */
    .step-active { color: #2563eb; font-weight: bold; }
    .step-done { color: #10b981; font-weight: bold; }
    .step-pending { color: #94a3b8; }
    
    /* Streamlit Button override for premium look */
    div.stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        padding: 12px 28px !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 20px 25px -5px rgba(37, 99, 235, 0.4) !important;
        border: none !important;
    }
    div.stButton > button:active {
        transform: translateY(0px) !important;
    }
</style>
""", unsafe_allow_html=True)

# App Title
st.markdown('<div class="main-title">🛒 QuickCart Feedback Intelligence Pipeline</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Production-Quality Customer Feedback Audit, Cleaning, AI Enrichment, and Verification Layer</div>', unsafe_allow_html=True)

st.info("💡 **Core Philosophy:** *I intentionally treated the dataset as untrusted. Before applying AI, I measured data quality, quantified complaint inflation, validated AI outputs, and only then generated business insights.*")

# Sidebar - Configuration and Source Info
st.sidebar.header("Pipeline Configurations")

# Upload logic
st.sidebar.write("### Dataset Upload")
uploaded_file = st.sidebar.file_uploader("Upload feedback CSV or Excel file", type=["csv", "xlsx", "xls"])

# Load raw dataframe
df_raw = None
source_name = ""

if uploaded_file is not None:
    try:
        file_name = uploaded_file.name.lower()
        if file_name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        elif file_name.endswith(('.xlsx', '.xls')):
            df_raw = pd.read_excel(uploaded_file)
        else:
            st.sidebar.error("Unsupported file format. Please upload a CSV or Excel file.")
            
        if df_raw is not None:
            source_name = uploaded_file.name
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")

if df_raw is not None:
    # Check if the uploaded file has changed. If so, reset the pipeline execution state.
    current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if 'last_uploaded_file' not in st.session_state or st.session_state['last_uploaded_file'] != current_file_id:
        st.session_state['last_uploaded_file'] = current_file_id
        st.session_state['pipeline_run'] = False
        for key in ['cleaned_df', 'cleaning_log', 'validated_df', 'corrections_log', 'validation_metrics', 'distributions', 'crosstabs', 'conflicts', 'trends', 'recommendations']:
            if key in st.session_state:
                del st.session_state[key]

    st.sidebar.success(f"Loaded {len(df_raw)} records from:\n`{source_name}`")
    
    # Run audit on raw data immediately to showcase Data Skepticism
    raw_audit = audit_dataset(df_raw)
    
    # Store state in session state to persist between button clicks
    if 'pipeline_run' not in st.session_state:
        st.session_state['pipeline_run'] = False
        
    st.write("### Data Quality Audit (Pre-Processing)")
    st.write("An assessment of the raw feedback file before cleaning and AI analysis. Management can review these raw anomalies to estimate raw dataset reliability.")
    
    # Row for raw data quality stats
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 10px; margin-bottom: 16px;">
        <div class="kpi-card">
            <div class="kpi-header">Total Raw Records</div>
            <div class="kpi-value kpi-highlight-blue">{raw_audit['total_records']}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Total records in file</div>
        </div>
        <div class="kpi-card" title="Measures input file data quality and integrity (penalizing missing values, invalid timestamps, duplicates, and empty text), NOT customer satisfaction.">
            <div class="kpi-header">Raw Dataset Health</div>
            <div class="kpi-value kpi-highlight-green">{raw_audit['health_score']}%</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Data Integrity Index</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">Duplicate Rows (Exact)</div>
            <div class="kpi-value kpi-highlight-orange">{raw_audit['duplicate_row_count']}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Identical rows found</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">Empty/Meaningless Reviews</div>
            <div class="kpi-value kpi-highlight-red">{raw_audit['empty_feedback_count']}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Meaningless feedback rows</div>
        </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
        <div class="kpi-card">
            <div class="kpi-header">Missing Timestamps</div>
            <div class="kpi-value kpi-highlight-orange">{raw_audit['missing_timestamp_count']}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Null dates filled chronologically</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">Missing Ratings</div>
            <div class="kpi-value kpi-highlight-orange">{raw_audit['missing_rating_count']}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Imputed ratings based on text tone</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">Duplicate Feedback Text</div>
            <div class="kpi-value kpi-highlight-orange">{raw_audit['duplicate_feedback_count']}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Near-duplicates identified</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">Invalid Dates</div>
            <div class="kpi-value kpi-highlight-red">{raw_audit['invalid_timestamp_count']}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Unparseable date strings</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Contradiction callout
    if raw_audit['contradiction_count'] > 0:
        st.warning(f"⚠️ **Heuristic Anomaly Alert:** Detected **{raw_audit['contradiction_count']}** potential rating vs text contradictions (e.g. 5-star reviews containing negative complain words). This indicates sarcasm or user UI error.")

    # Execution controls
    st.write("---")
    st.write("### Processing Control Panel")
    
    run_btn = st.button("🚀 Execute Pipeline (Audit → Clean → AI Enrich → Validate → Analyze)", type="primary")
    
    if run_btn or st.session_state['pipeline_run']:
        st.session_state['pipeline_run'] = True
        
        # We only run actual execution if button was clicked; otherwise we read from session state if already computed
        if 'cleaned_df' not in st.session_state or run_btn:
            reset_api_circuit()
            # Step visualizer setup
            step_placeholder = st.empty()
            
            def update_steps(active_step):
                steps = [
                    ("1. Data Quality Audit", 1),
                    ("2. Cleaning & Deduplication", 2),
                    ("3. AI Sentiment & Category Enrichment", 3),
                    ("4. Verification & Validation Layer", 4),
                    ("5. Insights and Reporting Engine", 5)
                ]
                html_out = "<div style='display: flex; gap: 20px; font-size: 0.9rem; margin-bottom: 20px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;'>"
                for name, num in steps:
                    if num < active_step:
                        html_out += f"<span class='step-done'>✓ {name}</span>"
                    elif num == active_step:
                        html_out += f"<span class='step-active'>⏳ {name}</span>"
                    else:
                        html_out += f"<span class='step-pending'>{name}</span>"
                html_out += "</div>"
                step_placeholder.markdown(html_out, unsafe_allow_html=True)

            # Execution logic
            # Step 1: Audit
            update_steps(1)
            time.sleep(0.5) # Simulating fast parsing
            
            # Step 2: Cleaning
            update_steps(2)
            cleaned_df, cleaning_log = clean_dataset(df_raw)
            time.sleep(0.5)
            
            # Step 3: Enrichment
            update_steps(3)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def report_progress(current, total):
                progress_bar.progress(current / total)
                status_text.text(f"Enriching record {current} of {total}...")
                
            enriched_df = enrich_dataset(cleaned_df, progress_callback=report_progress)
            progress_bar.empty()
            status_text.empty()
            
            # Step 4: Validation
            update_steps(4)
            validated_df, corrections_log, validation_metrics = validate_and_correct_dataset(
                enriched_df, health_score=raw_audit['health_score']
            )
            time.sleep(0.5)
            
            # Step 5: Insights
            update_steps(5)
            distributions = compute_distributions(validated_df)
            crosstabs = compute_crosstabs(validated_df)
            conflicts = analyze_rating_sentiment_conflicts(validated_df)
            trends = analyze_trends(validated_df)
            recommendations = generate_recommendations(validated_df, distributions, conflicts, trends)
            
            # Generate HTML/MD Reports (in-memory only, no disk writes)
            html_report = generate_html_report(raw_audit, cleaning_log, validation_metrics, distributions, conflicts, trends, recommendations)
            
            # Mark step complete
            update_steps(6)
            
            # Store everything in session state (no local files written)
            st.session_state['cleaned_df'] = cleaned_df
            st.session_state['cleaning_log'] = cleaning_log
            st.session_state['validated_df'] = validated_df
            st.session_state['corrections_log'] = corrections_log
            st.session_state['validation_metrics'] = validation_metrics
            st.session_state['distributions'] = distributions
            st.session_state['crosstabs'] = crosstabs
            st.session_state['conflicts'] = conflicts
            st.session_state['trends'] = trends
            st.session_state['recommendations'] = recommendations
            st.session_state['enriched_csv_bytes'] = validated_df.to_csv(index=False).encode('utf-8')
            st.session_state['html_report'] = html_report if html_report else ""
        
        # Read from session state
        cleaned_df = st.session_state['cleaned_df']
        cleaning_log = st.session_state['cleaning_log']
        validated_df = st.session_state['validated_df']
        corrections_log = st.session_state['corrections_log']
        validation_metrics = st.session_state['validation_metrics']
        distributions = st.session_state['distributions']
        crosstabs = st.session_state['crosstabs']
        conflicts = st.session_state['conflicts']
        trends = st.session_state['trends']
        recommendations = st.session_state['recommendations']
        
        # Display Executive Dashboard
        st.write("### Executive Summary Dashboard")
        
        # Grid 1: Audit and Confidence metrics
        cols1 = st.columns(5)
        
        # Unique complaint patterns (by normalized_text)
        unique_complaint_count = int(validated_df['normalized_text'].nunique()) if 'normalized_text' in validated_df.columns else len(validated_df)
        # Deduplicated records = empty + exact removed + non-unique normalized rows
        total_removed = cleaning_log['empty_removed'] + cleaning_log['exact_duplicates_removed']
        reduction_pct = round((total_removed / raw_audit['total_records']) * 100, 1) if raw_audit['total_records'] > 0 else 0.0
        
        with cols1[0]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">Raw Records Received</div>
                <div class="kpi-value kpi-highlight-blue">{raw_audit['total_records']}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Total feedback input volume</div>
            </div>
            """, unsafe_allow_html=True)
            
        with cols1[1]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">Valid Complaints</div>
                <div class="kpi-value kpi-highlight-blue">{len(validated_df)}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">{unique_complaint_count} unique complaint patterns</div>
            </div>
            """, unsafe_allow_html=True)
            
        with cols1[2]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">Records Removed</div>
                <div class="kpi-value kpi-highlight-orange">{total_removed}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Empty & exact duplicates cleaned</div>
            </div>
            """, unsafe_allow_html=True)
            
        with cols1[3]:
            st.markdown(f"""
            <div class="kpi-card" title="Measures input file data quality and integrity (e.g. duplicates, missing values), NOT customer satisfaction.">
                <div class="kpi-header">Dataset Health Score</div>
                <div class="kpi-value kpi-highlight-green">{raw_audit['health_score']}%</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Data Quality & Integrity Index</div>
            </div>
            """, unsafe_allow_html=True)
            
        with cols1[4]:
            rel_str = validation_metrics['insight_reliability']
            rel_class = f"rel-{rel_str.lower().replace(' ', '-')}"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">Insight Reliability</div>
                <div style="margin-top: 8px;">
                    <span class="reliability-badge {rel_class}">{rel_str}</span>
                </div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 14px;">Data Quality + AI Confidence</div>
            </div>
            """, unsafe_allow_html=True)

        if rel_str == "Limited by Source Data Quality":
            st.warning("⚠️ **Insight Reliability Notice:** The system worked correctly. However, the source dataset contained substantial quality issues such as duplicate complaints, missing ratings, and incomplete timestamps. Therefore the insights should be interpreted with appropriate caution.")
            
        # Business Impact Summary card
        st.markdown(f"""
        <div style="background-color: #eff6ff; border-left: 5px solid #2563eb; border-radius: 8px; padding: 20px; margin-top: 10px; margin-bottom: 24px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);">
            <h4 style="margin: 0 0 12px 0; color: #1e3a8a; font-weight: 700; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.05em;">📊 Business Impact Summary</h4>
            <p style="margin: 0; color: #1e40af; font-size: 0.95rem; line-height: 1.6; font-weight: 500;">
                💡 <strong>Data Quality Value:</strong> From <strong>{raw_audit['total_records']}</strong> raw feedback records, we removed <strong>{total_removed}</strong> empty or exact duplicate records, retaining <strong>{len(validated_df)}</strong> valid complaints for AI analysis. These {len(validated_df)} records map to <strong>{unique_complaint_count} unique underlying complaint patterns</strong> — each enriched with AI sentiment, category, and confidence scores. The <code>complaint_count</code> column tracks how many customers reported each issue.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Grid 2: Business Findings Summary
        cols2 = st.columns(4)
        
        # Top Category logic
        top_cat = max(distributions['category'], key=lambda k: distributions['category'][k]['Count'])
        top_cat_pct = distributions['category'][top_cat]['Percentage']
        
        # Most Negative Source logic
        neg_sources = {}
        for src, sent_data in crosstabs['source_vs_sentiment'].items():
            neg_sources[src] = sent_data.get('Negative', 0.0)
        most_neg_src = max(neg_sources, key=neg_sources.get) if neg_sources else "N/A"
        most_neg_src_pct = neg_sources[most_neg_src] if neg_sources else 0.0
        
        with cols2[0]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">Top Complaint Category</div>
                <div class="kpi-value" style="font-size: 1.4rem; padding: 6px 0;">{top_cat}</div>
                <div style="font-size: 0.75rem; color: #64748b;">Representing {top_cat_pct}% of cases</div>
            </div>
            """, unsafe_allow_html=True)
        with cols2[1]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">Most Negative Source</div>
                <div class="kpi-value" style="font-size: 1.4rem; padding: 6px 0;">{most_neg_src.replace('_', ' ').title()}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{most_neg_src_pct}% Negative sentiment</div>
            </div>
            """, unsafe_allow_html=True)
        with cols2[2]:
            trend_color_class = "kpi-highlight-green" if trends['status'] == "Improving" else ("kpi-highlight-red" if trends['status'] == "Worsening" else "kpi-highlight-orange")
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">Customer Sentiment Trend</div>
                <div class="kpi-value {trend_color_class}" style="font-size: 1.4rem; padding: 6px 0;">{trends['status']}</div>
                <div style="font-size: 0.75rem; color: #64748b; line-height: 1.2;">{trends['reason']}</div>
            </div>
            """, unsafe_allow_html=True)
        with cols2[3]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">Average AI Confidence</div>
                <div class="kpi-value kpi-highlight-orange">{round(validation_metrics['average_confidence'] * 100, 1)}%</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Corrections applied: {len(corrections_log)}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Analytics Visualization Section
        st.write("---")
        st.write("### Advanced Insights & Visualizations")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "Sentiment Insights", "Category Breakdown", "Trends Over Time", "Validation & Conflicts"
        ])
        
        # Tab 1: Sentiment
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### Sentiment Distribution")
                sent_df = pd.DataFrame.from_dict(distributions['sentiment'], orient='index').reset_index()
                fig_sent = px.pie(
                    sent_df, names='index', values='Count', 
                    color='index', color_discrete_map={'Positive': '#10b981', 'Neutral': '#94a3b8', 'Negative': '#ef4444'},
                    hole=0.45
                )
                fig_sent.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20), 
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=12)
                )
                st.plotly_chart(fig_sent, use_container_width=True)
            with col2:
                st.write("#### Source vs Sentiment Breakdown (%)")
                crosstab_sent_df = pd.DataFrame.from_dict(crosstabs['source_vs_sentiment'], orient='index')
                fig_src_sent = go.Figure()
                for sent_col in ['Positive', 'Neutral', 'Negative']:
                    color = '#10b981' if sent_col == 'Positive' else ('#ef4444' if sent_col == 'Negative' else '#94a3b8')
                    if sent_col in crosstab_sent_df.columns:
                        fig_src_sent.add_trace(go.Bar(
                            name=sent_col,
                            x=crosstab_sent_df.index,
                            y=crosstab_sent_df[sent_col],
                            marker_color=color
                        ))
                fig_src_sent.update_layout(
                    barmode='stack', 
                    margin=dict(t=20, b=20, l=20, r=20), 
                    height=350, 
                    yaxis_title="% Percent",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=11)
                )
                fig_src_sent.update_xaxes(showgrid=False)
                fig_src_sent.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
                st.plotly_chart(fig_src_sent, use_container_width=True)
                
        # Tab 2: Category
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### Primary Complaint Categories")
                cat_df = pd.DataFrame.from_dict(distributions['category'], orient='index').reset_index()
                # Sort categories by count
                cat_df = cat_df.sort_values('Count', ascending=True)
                fig_cat = px.bar(
                    cat_df, x='Count', y='index', orientation='h',
                    color='index', color_discrete_sequence=['#7c3aed', '#2563eb', '#10b981', '#f59e0b', '#64748b'],
                    labels={'index': 'Category'}
                )
                fig_cat.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20), 
                    height=350, 
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=12)
                )
                fig_cat.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
                fig_cat.update_yaxes(showgrid=False)
                st.plotly_chart(fig_cat, use_container_width=True)
            with col2:
                st.write("#### Source vs Category Distribution (%)")
                crosstab_cat_df = pd.DataFrame.from_dict(crosstabs['source_vs_category'], orient='index')
                fig_src_cat = go.Figure()
                for cat_col in config.ALLOWED_CATEGORIES:
                    if cat_col in crosstab_cat_df.columns:
                        fig_src_cat.add_trace(go.Bar(
                            name=cat_col,
                            x=crosstab_cat_df.index,
                            y=crosstab_cat_df[cat_col]
                        ))
                fig_src_cat.update_layout(
                    barmode='stack',
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=11)
                )
                fig_src_cat.update_xaxes(showgrid=False)
                fig_src_cat.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
                st.plotly_chart(fig_src_cat, use_container_width=True)
                
            st.write("---")
            st.write("#### 💬 Representative Feedback Examples per Category")
            cols_ex = st.columns(5)
            for i, cat in enumerate(config.ALLOWED_CATEGORIES):
                with cols_ex[i]:
                    st.write(f"**{cat}**")
                    cat_data = distributions['category'].get(cat, {})
                    examples = cat_data.get('Examples', [])
                    if examples:
                        for ex in examples:
                            st.caption(f"*\"{ex}\"*")
                    else:
                        st.caption("No examples available.")
                
        # Tab 3: Trends
        with tab3:
            st.write("#### Weekly Sentiment and Volume Trends")
            weekly_data = trends['weekly_data']
            if len(weekly_data) > 0:
                weekly_df = pd.DataFrame(weekly_data)
                
                # Plot line chart of negative sentiment ratio
                fig_trend = go.Figure()
                # Primary y-axis: Negative Sentiment Ratio
                fig_trend.add_trace(go.Scatter(
                    x=weekly_df['week_start'], y=weekly_df['negative_sentiment_percentage'],
                    name="Negative Sentiment (%)", line=dict(color='#ef4444', width=3),
                    yaxis='y1'
                ))
                # Secondary y-axis: Total volume
                fig_trend.add_trace(go.Bar(
                    x=weekly_df['week_start'], y=weekly_df['total_complaints'],
                    name="Total Complaints Count", marker_color='rgba(37, 99, 235, 0.2)',
                    yaxis='y2'
                ))
                
                fig_trend.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=11),
                    yaxis1=dict(
                        title=dict(text="Negative Sentiment %", font=dict(color="#ef4444", family="Plus Jakarta Sans, sans-serif")),
                        tickfont=dict(color="#ef4444", family="Plus Jakarta Sans, sans-serif"),
                        gridcolor='#f1f5f9'
                    ),
                    yaxis2=dict(
                        title=dict(text="Total Volume", font=dict(color="#2563eb", family="Plus Jakarta Sans, sans-serif")),
                        tickfont=dict(color="#2563eb", family="Plus Jakarta Sans, sans-serif"),
                        overlaying='y',
                        side='right',
                        gridcolor='#f1f5f9'
                    ),
                    legend=dict(x=0.01, y=0.99)
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No trend line available. Incomplete timestamp dataset.")
                
        # Tab 4: Conflicts
        with tab4:
            st.write("#### AI Validation & Sarcasm Conflicts")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.write("**Conflict Highlights**")
                st.metric("Contradiction Rate", f"{conflicts['conflict_percentage']}%")
                st.metric("Contradiction Count", conflicts['conflict_count'])
                st.write("""
                *Explanation:* Conflicting feedback represents cases where customers gave a high rating (e.g. 5 stars) but left strongly negative review text (such as "Charged twice, wonderful feature!").
                The validation layer detects this sarcasm and overrides the rating bias to ensure correct business prioritization.
                """)
            with col2:
                st.write("**Sample Contradiction Records**")
                if conflicts['conflicts_sample']:
                    sample_df = pd.DataFrame(conflicts['conflicts_sample'])
                    st.dataframe(sample_df, use_container_width=True)
                else:
                    st.info("No rating vs sentiment contradictions found.")

        # Human-in-the-Loop Panel
        st.write("---")
        st.write("### 👥 Human-in-the-Loop Validation")
        st.write(f"The validation layer flagged **{validation_metrics['low_confidence_count']}** low confidence records (confidence score < 0.70) that need direct human verification.")
        
        low_conf_df = validated_df[validated_df['needs_human_review']]
        if len(low_conf_df) > 0:
            st.dataframe(
                low_conf_df[['id', 'source', 'rating', 'feedback_text', 'ai_sentiment', 'ai_category', 'ai_confidence']],
                use_container_width=True
            )
        else:
            st.success("All AI classifications meet the target confidence threshold (>= 0.70)!")

        # Executive Recommendations Spotlight
        st.write("---")
        st.write("### 🏛️ Executive Recommendations")
        st.write("Prioritized strategic focus areas built for executive alignment:")
        
        # Calculate dynamic values
        cat_dist = distributions['category']
        ranked_cats = sorted(
            config.ALLOWED_CATEGORIES,
            key=lambda c: cat_dist.get(c, {}).get('Count', 0),
            reverse=True
        )

        CAT_REC_TEMPLATES = {
            'App Bug': {
                'title': 'App Bug Fixes',
                'recommendation': 'Focus engineering effort on crash reports, payment flow stability, and loading screen failures.',
                'color': '#d97706',
                'bg': '#fffbeb'
            },
            'Delivery': {
                'title': 'Courier SLAs',
                'recommendation': 'Review courier SLA compliance and delayed delivery hotspots.',
                'color': '#2563eb',
                'bg': '#eff6ff'
            },
            'Staff/Support': {
                'title': 'Support Workflows',
                'recommendation': 'Audit customer support workflows, hold times, and response templates to improve SLA compliance.',
                'color': '#10b981',
                'bg': '#f0fdf4'
            },
            'Billing': {
                'title': 'Billing & Refunds',
                'recommendation': 'Audit charge mechanisms, billing errors, and payment gateway double-deductions.',
                'color': '#7c3aed',
                'bg': '#f5f3ff'
            },
            'Other': {
                'title': 'General UX & Features',
                'recommendation': 'Address general user experience suggestions, logo feedback, and minor feature requests.',
                'color': '#4b5563',
                'bg': '#f9fafb'
            }
        }

        col_rec1, col_rec2, col_rec3 = st.columns(3)
        cols_rec = [col_rec1, col_rec2, col_rec3]
        
        for idx, cat in enumerate(ranked_cats[:3]):
            tmpl = CAT_REC_TEMPLATES.get(cat)
            pct = cat_dist.get(cat, {}).get('Percentage', 0.0)
            with cols_rec[idx]:
                st.markdown(f"""
                <div style="background-color: {tmpl['bg']}; border-left: 5px solid {tmpl['color']}; border-radius: 8px; padding: 18px; height: 185px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05);">
                    <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: {tmpl['color']}; margin-bottom: 8px;">Priority {idx + 1}</div>
                    <div style="font-weight: 700; font-size: 1.05rem; color: #0f172a; margin-bottom: 6px;">{tmpl['title']} ({pct}%)</div>
                    <div style="color: #4b5563; font-size: 0.9rem; line-height: 1.4;"><strong>Recommendation:</strong> {tmpl['recommendation']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.write("---")
        st.write("### 🎯 Detailed Actionable Recommendations")
        st.write("Granular automated recommendations generated from identified data anomalies, sentiment shifts, and UI conflicts:")
        
        for idx, rec in enumerate(recommendations):
            impact_lower = rec['impact'].lower()
            st.markdown(f"""
            <div class="rec-card rec-{impact_lower}">
                <div class="rec-meta">Recommendation {idx + 1} | {rec['impact']} Impact Level</div>
                <div class="rec-title">{rec['title']}</div>
                <div style="color: #4b5563; font-size: 0.92rem; line-height: 1.5;">{rec['description']}</div>
            </div>
            """, unsafe_allow_html=True)

        # Download Center (fully in-memory — no local files required)
        st.write("---")
        st.write("### 💾 Data & Report Download Center")
        
        col_down1, col_down2 = st.columns(2)
        
        with col_down1:
            csv_bytes = st.session_state.get('enriched_csv_bytes')
            if csv_bytes:
                st.download_button(
                    label="Download Enriched & Validated Feedback (CSV)",
                    data=csv_bytes,
                    file_name="enriched_feedback.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        with col_down2:
            html_report = st.session_state.get('html_report')
            if html_report:
                st.download_button(
                    label="Download Executive Summary Report (HTML)",
                    data=html_report,
                    file_name="summary_report.html",
                    mime="text/html",
                    use_container_width=True
                )
                    
else:
    st.markdown("""
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 40px; text-align: center; margin-top: 50px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        <h2 style="color: #0f172a; font-weight: 800; font-size: 1.8rem; margin-bottom: 12px;">📊 Welcome to QuickCart Feedback Intelligence</h2>
        <p style="color: #64748b; font-size: 1.05rem; margin-bottom: 30px; max-width: 600px; margin-left: auto; margin-right: auto;">
            To begin auditing, cleaning, and enriching customer reviews with AI insights, please upload a customer feedback file (.csv or .xlsx) in the sidebar.
        </p>
        <div style="display: flex; justify-content: center; gap: 24px; text-align: left; max-width: 750px; margin: 0 auto;">
            <div style="flex: 1; background-color: #ffffff; border: 1px solid #f1f5f9; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <h4 style="color: #2563eb; margin: 0 0 8px 0; font-weight: 700;">📂 Expected File Schema</h4>
                <ul style="color: #4b5563; font-size: 0.9rem; margin: 0; padding-left: 20px; line-height: 1.5;">
                    <li><strong>timestamp:</strong> Timestamp or date of review</li>
                    <li><strong>source:</strong> App Store, Google Play, Web, or Support</li>
                    <li><strong>rating:</strong> Numeric rating from 1 to 5</li>
                    <li><strong>feedback_text:</strong> Customer review comments</li>
                </ul>
            </div>
            <div style="flex: 1; background-color: #ffffff; border: 1px solid #f1f5f9; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <h4 style="color: #10b981; margin: 0 0 8px 0; font-weight: 700;">🚀 Key Capabilities</h4>
                <ul style="color: #4b5563; font-size: 0.9rem; margin: 0; padding-left: 20px; line-height: 1.5;">
                    <li>Detect and deduct rating/sentiment contradictions</li>
                    <li>Deduplicate & normalize repeat complaints</li>
                    <li>Batch-enriched AI classification with Groq Llama 3</li>
                    <li>Interactive summaries and download center</li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
