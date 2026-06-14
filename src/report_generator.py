from datetime import datetime
from src import config

def generate_markdown_report(audit_results, cleaning_log, validation_metrics, distributions, conflicts, trends, recommendations, output_path="summary_report.md"):
    """
    Generates a professional markdown report summarizing the findings.
    """
    total_raw = audit_results['total_records']
    total_cleaned = cleaning_log['total_cleaned_saved']
    
    # Calculate values
    reduction_pct = round((cleaning_log['normalized_duplicates_removed'] / total_raw) * 100, 1) if total_raw > 0 else 0.0
    
    # Dynamic date
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Dynamic values for executive recommendations
    cat_dist = distributions['category']
    ranked_cats = sorted(
        config.ALLOWED_CATEGORIES,
        key=lambda c: cat_dist.get(c, {}).get('Count', 0),
        reverse=True
    )

    CAT_REC_TEMPLATES = {
        'App Bug': {
            'title': 'App Bug Fixes',
            'recommendation': 'Focus engineering effort on crash reports, payment flow stability, and loading screen failures.'
        },
        'Delivery': {
            'title': 'Courier SLAs',
            'recommendation': 'Review courier SLA compliance and delayed delivery hotspots.'
        },
        'Staff/Support': {
            'title': 'Support Workflows',
            'recommendation': 'Audit customer support workflows, hold times, and response templates to improve compliance.'
        },
        'Billing': {
            'title': 'Billing & Refunds',
            'recommendation': 'Audit charge mechanisms, billing errors, and payment gateway double-deductions.'
        },
        'Other': {
            'title': 'General UX & Features',
            'recommendation': 'Address general user experience suggestions, logo feedback, and minor feature requests.'
        }
    }
    
    recs_md = ""
    for idx, cat in enumerate(ranked_cats[:3]):
        tmpl = CAT_REC_TEMPLATES.get(cat)
        pct = cat_dist.get(cat, {}).get('Percentage', 0.0)
        recs_md += f"**Priority {idx + 1}: {tmpl['title']} ({pct}% of issues)**\n*Recommendation:* {tmpl['recommendation']}\n\n"

    md = f"""# QuickCart Customer Feedback Intelligence Report
*Generated: {current_date} (Autonomous Pipeline)*

---

## 1. Executive Summary

| KPI | Value | Business Context |
| :--- | :--- | :--- |
| **Total Records (Raw)** | {total_raw} | Total tickets collected from all sources |
| **Total Unique Complaint Patterns** | {total_cleaned} | Consolidated distinct customer complaint patterns |
| **Dataset Health Score** | {audit_results['health_score']}% | Deductive measure of raw data quality |
| **Average AI Confidence** | {round(validation_metrics['average_confidence'] * 100, 1)}% | Confidence level of the AI enrichment layer |
| **Insight Reliability** | **{validation_metrics['insight_reliability']}** | Confidence rating of findings |
| **Sentiment Trend** | **{trends['status']}** | Directional flow of customer negative feedback |
"""

    if validation_metrics['insight_reliability'] == "Limited by Source Data Quality":
        md += """
> [!WARNING]
> **Insight Reliability Notice:** The system worked correctly. However, the source dataset contained substantial quality issues such as duplicate complaints, missing ratings, and incomplete timestamps. Therefore the insights should be interpreted with appropriate caution.
"""

    md += f"""
### Overall Trend Summary:
**{trends['reason']}**

---

## 2. Business Impact Summary (Deduplication Value)

Without cleaning, management would believe there were **{total_raw}** independent complaints. After normalization and deduplication, we identified **{total_cleaned}** unique complaint patterns. This demonstrates how poor data quality can distort business decisions:

- **Raw Records received:** {total_raw}
- **Distinct Complaint Patterns identified:** {total_cleaned}
- **Complaint Inflation Removed:** {cleaning_log['normalized_duplicates_removed']} records
- **Overall Volume Reduction:** {reduction_pct}%

---

## 3. Data Quality Audit & Cleaning Decisions

### Data Quality Findings (Raw Dataset):
- **Missing Timestamps:** {audit_results['missing_timestamp_count']} records
- **Missing Ratings:** {audit_results['missing_rating_count']} records
- **Duplicate Rows:** {audit_results['duplicate_row_count']} records
- **Duplicate Feedback (Raw):** {audit_results['duplicate_feedback_count']} records
- **Empty / Placeholder Feedback:** {audit_results['empty_feedback_count']} records
- **Invalid Timestamps:** {audit_results['invalid_timestamp_count']} records
- **Rating vs Text Sentiment Contradictions:** {audit_results['contradiction_count']} potential cases

### Cleaning Layer Operations & Decisions:
- Filtered out **{cleaning_log['empty_removed']}** empty/meaningless feedbacks to prevent categorization noise.
- Removed **{cleaning_log['exact_duplicates_removed']}** exact duplicate rows.
- Standardized **{cleaning_log['timestamps_standardized']}** timestamps to ISO format (`YYYY-MM-DD`).
- Normalized and deduplicated **{cleaning_log['normalized_duplicates_removed']}** redundant tickets (complaint inflation).
- Retained **{cleaning_log['unparseable_timestamps_kept']}** unparseable timestamp records for sentiment calculations, marking their dates as blank.

---

## 4. Sentiment & Category Analysis

### Sentiment Distribution:
"""
    for sent, data in distributions['sentiment'].items():
        md += f"- **{sent}:** {data['Count']} records ({data['Percentage']}%)\n"
        
    md += "\n### Category Distribution & Representative Examples:\n"
    for cat, data in distributions['category'].items():
        md += f"#### **{cat}** ({data['Count']} records, {data['Percentage']}%)\n"
        if data.get('Examples'):
            md += "*Representative Customer Comments:*\n"
            for ex in data['Examples']:
                md += f"- *\"{ex}\"*\n"
        md += "\n"
        
    md += f"""
### Rating vs Sentiment Contradiction Rate:
- **Contradiction Count:** {conflicts['conflict_count']} records
- **Contradiction Percentage:** {conflicts['conflict_percentage']}%
- *Sarcasm Flag:* Customers gave a high rating (4-5) but left heavily negative comments (or vice-versa). The system detected these contradictions and appropriately classified their sentiment based on the text.

---

## 5. Executive Recommendations

Based on complaint volumes and category hotspots, the following consulting-level recommendations are prioritized:

{recs_md}
"""

    md += f"""
---

## 6. Detailed Technical & Actionable Recommendations
"""
    for idx, rec in enumerate(recommendations):
        md += f"\n### [{rec['impact']}] Recommendation {idx+1}: {rec['title']}\n"
        md += f"**Description:** {rec['description']}\n"
        
    return md


def generate_html_report(audit_results, cleaning_log, validation_metrics, distributions, conflicts, trends, recommendations):
    """
    Generates a beautiful, highly interactive, client-side rendered HTML report.
    """
    import json
    
    # Bundle data into a single dictionary
    report_data = {
        'audit_results': audit_results,
        'cleaning_log': cleaning_log,
        'validation_metrics': validation_metrics,
        'distributions': distributions,
        'conflicts': conflicts,
        'trends': trends,
        'recommendations': recommendations
    }
    
    # Serialize to JSON string
    data_json = json.dumps(report_data, ensure_ascii=False)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickCart Feedback Report</title>
    <!-- Premium Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Chart.js CDN for interactive visualizations -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-color: #f8fafc;
            --container-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
            --primary-color: #2563eb;
            --primary-rgb: 37, 99, 235;
            --card-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.03), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
            --transition-speed: 0.25s;
        }}

        body.dark-mode {{
            --bg-color: #0f172a;
            --container-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --card-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25), 0 8px 10px -6px rgba(0, 0, 0, 0.25);
        }}

        body {{
            font-family: 'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 30px 20px;
            transition: background-color var(--transition-speed), color var(--transition-speed);
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: var(--container-bg);
            border-radius: 24px;
            box-shadow: var(--card-shadow);
            padding: 40px;
            border: 1px solid var(--border-color);
            transition: background-color var(--transition-speed), border-color var(--transition-speed), box-shadow var(--transition-speed);
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}

        .header-title h1 {{
            margin: 0;
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            font-size: 2.1rem;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .header-title .meta {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 8px;
            font-weight: 500;
        }}

        .theme-toggle {{
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            padding: 10px 20px;
            border-radius: 9999px;
            color: var(--text-main);
            cursor: pointer;
            font-weight: 600;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all var(--transition-speed);
        }}

        .theme-toggle:hover {{
            background-color: var(--border-color);
            transform: translateY(-1px);
        }}

        /* KPI Container */
        .kpi-container {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 35px;
        }}

        @media (max-width: 768px) {{
            .kpi-container {{
                grid-template-columns: 1fr;
            }}
        }}

        .kpi-card {{
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px 20px;
            text-align: center;
            background-color: var(--bg-color);
            transition: transform var(--transition-speed), border-color var(--transition-speed), box-shadow var(--transition-speed);
        }}

        .kpi-card:hover {{
            transform: translateY(-3px);
            box-shadow: var(--card-shadow);
            border-color: rgba(var(--primary-rgb), 0.4);
        }}

        .kpi-title {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 700;
        }}

        .kpi-val {{
            font-size: 1.8rem;
            font-weight: 800;
            margin-top: 10px;
            color: var(--primary-color);
            letter-spacing: -0.02em;
            font-family: 'Outfit', sans-serif;
        }}

        .reliability-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
        }}
        
        .rel-high {{ background-color: #d1fae5; color: #065f46; }}
        .rel-medium {{ background-color: #fef3c7; color: #92400e; }}
        .rel-low, .rel-limited-by-source-data-quality {{ background-color: #fee2e2; color: #991b1b; }}

        .reliability-warning {{
            background-color: #fffbeb;
            border-left: 4px solid #f59e0b;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 24px;
            display: none; /* Show dynamically if low reliability */
        }}
        
        body.dark-mode .reliability-warning {{
            background-color: rgba(245, 158, 11, 0.05);
        }}

        .trend-callout {{
            background-color: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 32px;
        }}
        
        body.dark-mode .trend-callout {{
            background-color: rgba(59, 130, 246, 0.05);
        }}

        /* Business Impact deduplication value card */
        .impact-card {{
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.03) 0%, rgba(124, 58, 237, 0.03) 100%);
            border: 1px solid var(--border-color);
            padding: 24px;
            border-radius: 16px;
            margin-bottom: 35px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.01);
        }}

        .impact-metrics {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-top: 20px;
            text-align: center;
        }}

        @media (max-width: 600px) {{
            .impact-metrics {{
                grid-template-columns: 1fr 1fr;
            }}
        }}

        .impact-subcard {{
            background: var(--container-bg);
            padding: 16px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            transition: all var(--transition-speed);
        }}
        .impact-subcard:hover {{
            transform: translateY(-2px);
            border-color: rgba(var(--primary-rgb), 0.3);
        }}

        .impact-subcard .lbl {{
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 700;
        }}

        .impact-subcard .val {{
            font-size: 1.35rem;
            font-weight: 800;
            margin-top: 6px;
            font-family: 'Outfit', sans-serif;
        }}

        /* Section Headings */
        h2 {{
            font-size: 1.4rem;
            color: var(--text-main);
            margin-top: 48px;
            margin-bottom: 20px;
            font-weight: 750;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: -0.02em;
            font-family: 'Outfit', sans-serif;
        }}

        h2::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border-color);
        }}

        /* Tables styling */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 32px;
            font-size: 0.925rem;
        }}

        th, td {{
            text-align: left;
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-weight: 700;
        }}

        tr:hover td {{
            background-color: rgba(37, 99, 235, 0.02);
        }}

        /* Visualizations */
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 35px;
        }}

        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .chart-card {{
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            background-color: var(--container-bg);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.01);
        }}

        .chart-card h3 {{
            margin-top: 0;
            margin-bottom: 16px;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-main);
        }}

        .full-width-chart {{
            grid-column: 1 / -1;
        }}

        .chart-wrapper {{
            position: relative;
            height: 250px;
            width: 100%;
        }}

        .full-width-chart .chart-wrapper {{
            height: 300px;
        }}

        /* Dynamic Category Comment Tabs */
        .tabs-header {{
            display: flex;
            gap: 8px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
            margin-bottom: 20px;
            overflow-x: auto;
            scrollbar-width: thin;
        }}

        .tab-btn {{
            background: none;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            transition: all var(--transition-speed);
        }}

        .tab-btn:hover {{
            color: var(--text-main);
            background-color: var(--bg-color);
        }}

        .tab-btn.active {{
            color: #ffffff;
            background-color: var(--primary-color);
        }}

        .comments-list-box {{
            background-color: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px 24px;
            min-height: 120px;
            transition: background-color var(--transition-speed), border-color var(--transition-speed);
        }}

        .comments-list-box ul {{
            margin: 0;
            padding-left: 20px;
            color: var(--text-main);
            font-style: italic;
            line-height: 1.6;
        }}

        .comments-list-box li {{
            margin-bottom: 10px;
        }}
        
        .comments-list-box li:last-child {{
            margin-bottom: 0;
        }}

        /* Recommendations List */
        .recs-list {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 16px;
        }}

        .rec-card {{
            border-left: 5px solid #9ca3af;
            padding: 16px 20px;
            background-color: var(--bg-color);
            border-radius: 0 12px 12px 0;
            border-top: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.01);
            transition: transform var(--transition-speed);
        }}

        .rec-card:hover {{
            transform: translateX(4px);
        }}

        .rec-card.critical {{ border-left-color: #ef4444; }}
        .rec-card.high {{ border-left-color: #f59e0b; }}
        .rec-card.medium {{ border-left-color: #3b82f6; }}
        .rec-card.low {{ border-left-color: #10b981; }}

        .rec-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}

        .rec-header h4 {{
            margin: 0;
            font-size: 1.05rem;
            font-weight: 700;
        }}

        .badge {{
            padding: 4px 8px;
            border-radius: 9999px;
            font-size: 0.725rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .badge-critical {{ background-color: #fef2f2; color: #b91c1c; }}
        .badge-high {{ background-color: #fffbeb; color: #b45309; }}
        .badge-medium {{ background-color: #eff6ff; color: #1d4ed8; }}
        .badge-low {{ background-color: #f0fdf4; color: #15803d; }}

        .rec-desc {{
            margin: 0;
            font-size: 0.9rem;
            color: var(--text-muted);
            line-height: 1.5;
        }}

        /* Executive Spotlight */
        .spotlight-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }}

        @media (max-width: 768px) {{
            .spotlight-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .spotlight-card {{
            border-radius: 12px;
            padding: 16px;
            border-top: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            transition: all var(--transition-speed);
        }}

        .spotlight-card:hover {{
            transform: translateY(-2px);
        }}

        .spotlight-priority {{
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}

        .spotlight-title {{
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 8px;
            font-family: 'Outfit', sans-serif;
        }}

        .spotlight-desc {{
            font-size: 0.85rem;
            line-height: 1.45;
        }}
    </style>
</head>
<body>
    <!-- Embedded JSON Data Payload -->
    <script id="report-data" type="application/json">
    {data_json}
    </script>

    <div class="container">
        <header>
            <div class="header-title">
                <h1>QuickCart Customer Feedback Intelligence Report</h1>
                <div class="meta" id="report-meta">Generated: {datetime.now().strftime('%Y-%m-%d')} | Processing Provider: Autonomous Pipeline</div>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()" id="theme-btn">
                <span>🌙</span> Dark Mode
            </button>
        </header>

        <h2>1. Executive Summary</h2>
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-title">Raw Records</div>
                <div class="kpi-val" id="kpi-raw">-</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Dataset Health</div>
                <div class="kpi-val" id="kpi-health">-</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Insight Reliability</div>
                <div style="margin-top: 10px;">
                    <span class="reliability-badge" id="kpi-reliability">-</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Unique Complaint Patterns</div>
                <div class="kpi-val" id="kpi-unique">-</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">AI Confidence</div>
                <div class="kpi-val" id="kpi-confidence">-</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Sentiment Trend</div>
                <div class="kpi-val" id="kpi-trend">-</div>
            </div>
        </div>

        <div class="reliability-warning" id="reliability-alert">
            <strong style="color: #b45309;">Insight Reliability Notice:</strong>
            <p style="margin: 4px 0 0 0; color: #78350f; font-size: 0.9rem;">The system worked correctly. However, the source dataset contained substantial data quality issues (such as duplicate complaints, missing ratings, and unparseable dates). Therefore, downstream insights and recommendations should be interpreted with appropriate caution.</p>
        </div>

        <div class="trend-callout">
            <strong style="color: #1d4ed8;">Sentiment Trend Direction:</strong>
            <p style="margin: 4px 0 0 0; color: #1e3a8a; font-size: 0.95rem;" id="trend-text"></p>
        </div>

        <h2>2. Business Impact Summary (Deduplication Value)</h2>
        <div class="impact-card">
            <p style="margin: 0 0 12px 0; color: #1e40af; font-size: 1.05rem; font-weight: 600;">Deduplication Value:</p>
            <p style="margin: 0 0 20px 0; color: #1e3a8a; line-height: 1.6; font-size: 0.95rem;" id="impact-paragraph">
                Without cleaning, management would believe there were independent complaints.
            </p>
            <div class="impact-metrics">
                <div class="impact-subcard">
                    <div class="lbl">Raw Records</div>
                    <div class="val" id="impact-raw">-</div>
                </div>
                <div class="impact-subcard">
                    <div class="lbl" style="color: #10b981;">Unique Complaint Patterns</div>
                    <div class="val" id="impact-unique" style="color: #10b981;">-</div>
                </div>
                <div class="impact-subcard">
                    <div class="lbl" style="color: #f59e0b;">Inflation Removed</div>
                    <div class="val" id="impact-removed" style="color: #f59e0b;">-</div>
                </div>
                <div class="impact-subcard">
                    <div class="lbl" style="color: #ef4444;">Reduction %</div>
                    <div class="val" id="impact-reduction" style="color: #ef4444;">-</div>
                </div>
            </div>
        </div>

        <h2>3. Data Quality Audit & Cleaning Operations</h2>
        <table>
            <thead>
                <tr>
                    <th>Data Quality Issue</th>
                    <th>Affected Count</th>
                    <th>Cleaning Action Taken</th>
                </tr>
            </thead>
            <tbody id="audit-table-body">
                <!-- Populated dynamically -->
            </tbody>
        </table>

        <h2>4. Insights and Visualizations</h2>
        <div class="charts-grid">
            <div class="chart-card">
                <h3>Sentiment Split</h3>
                <div class="chart-wrapper">
                    <canvas id="sentimentChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>Complaint Categories</h3>
                <div class="chart-wrapper">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>
            <div class="chart-card full-width-chart">
                <h3>Weekly Sentiment and Volume Trends</h3>
                <div class="chart-wrapper" id="trend-chart-wrapper">
                    <canvas id="trendChart"></canvas>
                </div>
                <div id="no-trend-message" style="display: none; padding: 30px; text-align: center; color: var(--text-muted);">
                    No trend visualization available due to missing or incomplete date parameters in the source dataset.
                </div>
            </div>
        </div>

        <h3 style="margin-top: 32px; font-weight: 700; font-size: 1.15rem;">💬 Representative Customer Feedback Comments</h3>
        <div class="comments-section">
            <div class="tabs-header" id="comments-tabs">
                <!-- Dynamically generated buttons -->
            </div>
            <div class="comments-list-box">
                <ul id="comments-list-content">
                    <!-- Populated dynamically based on tab clicks -->
                </ul>
            </div>
        </div>

        <h3 style="margin-top: 32px; font-weight: 700; font-size: 1.15rem;">Rating vs Text Sentiment Contradictions</h3>
        <div class="contradictions-box">
            <ul style="margin: 0; padding-left: 20px; line-height: 1.6; font-size: 0.925rem;">
                <li><strong>Total Contradiction Cases Found:</strong> <span id="contradiction-count">-</span></li>
                <li><strong>Percentage of Contradictory Records:</strong> <span id="contradiction-pct">-</span>%</li>
                <li><strong>Impact:</strong> Highlights customers expressing frustration in reviews but selecting high star ratings (sarcasm/UI errors). The system detected these contradictions and appropriately classified their sentiment based on the text.</li>
            </ul>
        </div>

        <h2>5. Executive Recommendations (Consultant Spotlight)</h2>
        <div class="spotlight-grid" id="spotlight-container">
            <!-- Dynamically populated -->
        </div>

        <h2>6. Detailed Technical & Actionable Recommendations</h2>
        <div class="recs-list" id="recs-container">
            <!-- Dynamically populated -->
        </div>
    </div>

    <!-- Client-side Rendering Logic -->
    <script>
        // Theme switching logic
        function toggleTheme() {{
            const body = document.body;
            body.classList.toggle('dark-mode');
            const themeBtn = document.getElementById('theme-btn');
            if (body.classList.contains('dark-mode')) {{
                themeBtn.innerHTML = '<span>☀️</span> Light Mode';
            }} else {{
                themeBtn.innerHTML = '<span>🌙</span> Dark Mode';
            }}
            
            // Re-render charts to adjust text colors
            if (window.sentimentChartInst) {{
                updateChartThemes();
            }}
        }}

        function updateChartThemes() {{
            const isDark = document.body.classList.contains('dark-mode');
            const textColor = isDark ? '#f8fafc' : '#0f172a';
            const gridColor = isDark ? '#334155' : '#e2e8f0';

            const charts = [window.sentimentChartInst, window.categoryChartInst, window.trendChartInst];
            charts.forEach(chart => {{
                if (!chart) return;
                
                // Update text options
                if (chart.options.plugins && chart.options.plugins.legend) {{
                    chart.options.plugins.legend.labels.color = textColor;
                }}
                
                // Update scales options if they exist
                if (chart.options.scales) {{
                    for (let key in chart.options.scales) {{
                        const scale = chart.options.scales[key];
                        if (scale.ticks) scale.ticks.color = textColor;
                        if (scale.grid) scale.grid.color = gridColor;
                        if (scale.title) scale.title.color = textColor;
                    }}
                }}
                chart.update();
            }});
        }}

        // Main Rendering Logic
        document.addEventListener('DOMContentLoaded', () => {{
            // Load and parse embedded data
            const payload = JSON.parse(document.getElementById('report-data').textContent);
            const {{ audit_results, cleaning_log, validation_metrics, distributions, conflicts, trends, recommendations }} = payload;

            // 1. Render KPIs
            const totalRaw = audit_results.total_records;
            const totalCleaned = cleaning_log.total_cleaned_saved;
            const reductionPct = totalRaw > 0 ? ((cleaning_log.normalized_duplicates_removed / totalRaw) * 100).toFixed(1) : 0.0;

            document.getElementById('kpi-raw').textContent = totalRaw;
            document.getElementById('kpi-health').textContent = audit_results.health_score + '%';
            
            const relBadge = document.getElementById('kpi-reliability');
            relBadge.textContent = validation_metrics.insight_reliability;
            const reliabilityClass = 'rel-' + validation_metrics.insight_reliability.toLowerCase().replace(/ /g, '-');
            relBadge.classList.add(reliabilityClass);

            if (validation_metrics.insight_reliability === 'Limited by Source Data Quality') {{
                document.getElementById('reliability-alert').style.display = 'block';
            }}

            document.getElementById('kpi-unique').textContent = totalCleaned;
            document.getElementById('kpi-confidence').textContent = (validation_metrics.average_confidence * 100).toFixed(1) + '%';
            
            const trendVal = document.getElementById('kpi-trend');
            trendVal.textContent = trends.status;
            if (trends.status === 'Worsening') {{
                trendVal.style.color = '#ef4444';
            }} else if (trends.status === 'Improving') {{
                trendVal.style.color = '#10b981';
            }} else {{
                trendVal.style.color = '#f59e0b';
            }}

            document.getElementById('trend-text').textContent = trends.reason;

            // 2. Business Impact
            document.getElementById('impact-paragraph').innerHTML = `Without cleaning, management would believe there were <strong>${{totalRaw}}</strong> independent complaints. After normalization and deduplication, we identified <strong>${{totalCleaned}}</strong> unique complaint patterns. This <strong>${{reductionPct}}% reduction</strong> demonstrates how poor data quality can distort business decisions.`;
            document.getElementById('impact-raw').textContent = totalRaw;
            document.getElementById('impact-unique').textContent = totalCleaned;
            document.getElementById('impact-removed').textContent = cleaning_log.normalized_duplicates_removed;
            document.getElementById('impact-reduction').textContent = reductionPct + '%';

            // 3. Data Quality Table
            const auditData = [
                {{ issue: 'Missing Timestamps', count: audit_results.missing_timestamp_count, action: 'Preserved; parsed dates set to Blank for weekly filters.' }},
                {{ issue: 'Missing Ratings', count: audit_results.missing_rating_count, action: 'Preserved; sentiment derived solely from feedback text.' }},
                {{ issue: 'Duplicate Rows (Exact)', count: audit_results.duplicate_row_count, action: `Removed <strong>${{cleaning_log.exact_duplicates_removed}}</strong> identical rows.` }},
                {{ issue: 'Duplicate Feedback Text (Near-Duplicates)', count: audit_results.duplicate_feedback_count, action: `Consolidated <strong>${{cleaning_log.normalized_duplicates_removed}}</strong> duplicate complaints; mapped to complaint volume counts.` }},
                {{ issue: 'Empty / Placeholder Feedback', count: audit_results.empty_feedback_count, action: `Removed <strong>${{cleaning_log.empty_removed}}</strong> meaningless comments.` }},
                {{ issue: 'Invalid Timestamp format', count: audit_results.invalid_timestamp_count, action: `Standardized <strong>${{cleaning_log.timestamps_standardized}}</strong> timestamps to ISO format.` }}
            ];
            
            const tableBody = document.getElementById('audit-table-body');
            auditData.forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.issue}}</td>
                    <td style="font-weight: 700;">${{row.count}}</td>
                    <td>${{row.action}}</td>
                `;
                tableBody.appendChild(tr);
            }});

            // 4. Rating Conflicts
            document.getElementById('contradiction-count').textContent = conflicts.conflict_count;
            document.getElementById('contradiction-pct').textContent = conflicts.conflict_percentage;

            // 5. Render Charts
            const isDark = document.body.classList.contains('dark-mode');
            const labelColor = isDark ? '#f8fafc' : '#0f172a';

            // Sentiment Chart
            const sentLabels = Object.keys(distributions.sentiment);
            const sentCounts = sentLabels.map(k => distributions.sentiment[k].Count);
            const sentColors = sentLabels.map(k => k === 'Positive' ? '#10b981' : (k === 'Negative' ? '#ef4444' : '#94a3b8'));
            
            const ctxSent = document.getElementById('sentimentChart').getContext('2d');
            window.sentimentChartInst = new Chart(ctxSent, {{
                type: 'doughnut',
                data: {{
                    labels: sentLabels,
                    datasets: [{{
                        data: sentCounts,
                        backgroundColor: sentColors,
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{ color: labelColor, font: {{ family: 'Plus Jakarta Sans', weight: '600' }} }}
                        }}
                    }},
                    cutout: '60%'
                }}
            }});

            // Category Chart
            const catLabels = Object.keys(distributions.category);
            const catCounts = catLabels.map(k => distributions.category[k].Count);
            
            const ctxCat = document.getElementById('categoryChart').getContext('2d');
            window.categoryChartInst = new Chart(ctxCat, {{
                type: 'bar',
                data: {{
                    labels: catLabels,
                    datasets: [{{
                        label: 'Complaint Count',
                        data: catCounts,
                        backgroundColor: '#3b82f6',
                        borderRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{ beginAtZero: true, grid: {{ color: '#e2e8f0' }}, ticks: {{ color: labelColor }} }},
                        x: {{ grid: {{ display: false }}, ticks: {{ color: labelColor }} }}
                    }},
                    plugins: {{
                        legend: {{ display: false }}
                    }}
                }}
            }});

            // Trend Chart
            const weeklyData = trends.weekly_data || [];
            if (weeklyData.length > 0) {{
                const weekLabels = weeklyData.map(d => d.week_start);
                const ratioData = weeklyData.map(d => d.negative_sentiment_percentage);
                const volumeData = weeklyData.map(d => d.total_complaints);

                const ctxTrend = document.getElementById('trendChart').getContext('2d');
                window.trendChartInst = new Chart(ctxTrend, {{
                    type: 'line',
                    data: {{
                        labels: weekLabels,
                        datasets: [
                            {{
                                label: 'Negative Sentiment Ratio (%)',
                                data: ratioData,
                                borderColor: '#ef4444',
                                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                borderWidth: 3,
                                fill: true,
                                yAxisID: 'y'
                            }},
                            {{
                                label: 'Volume (Tickets)',
                                data: volumeData,
                                type: 'bar',
                                backgroundColor: 'rgba(37, 99, 235, 0.15)',
                                hoverBackgroundColor: 'rgba(37, 99, 235, 0.3)',
                                borderRadius: 4,
                                yAxisID: 'y1'
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {{ display: true, text: 'Negative Sentiment Ratio (%)', color: '#ef4444' }},
                                ticks: {{ color: labelColor }},
                                grid: {{ color: '#e2e8f0' }}
                            }},
                            y1: {{
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {{ display: true, text: 'Volume (Tickets)', color: '#2563eb' }},
                                ticks: {{ color: labelColor }},
                                grid: {{ drawOnChartArea: false }}
                            }},
                            x: {{
                                grid: {{ display: false }},
                                ticks: {{ color: labelColor }}
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{ color: labelColor, font: {{ family: 'Plus Jakarta Sans', weight: '600' }} }}
                            }}
                        }}
                    }}
                }});
            }} else {{
                document.getElementById('trend-chart-wrapper').style.display = 'none';
                document.getElementById('no-trend-message').style.display = 'block';
            }}

            // 6. Dynamic Comments System
            const commentsTabs = document.getElementById('comments-tabs');
            const commentsContent = document.getElementById('comments-list-content');

            // Render category tabs dynamically
            catLabels.forEach((cat, index) => {{
                const btn = document.createElement('button');
                btn.className = 'tab-btn' + (index === 0 ? ' active' : '');
                btn.textContent = cat;
                btn.onclick = () => {{
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    renderComments(cat);
                }};
                commentsTabs.appendChild(btn);
            }});

            function renderComments(category) {{
                commentsContent.innerHTML = '';
                const catData = distributions.category[category];
                const examples = catData ? (catData.Examples || []) : [];
                
                if (examples.length > 0) {{
                    examples.forEach(ex => {{
                        const li = document.createElement('li');
                        li.innerHTML = `&ldquo;${{ex}}&rdquo;`;
                        commentsContent.appendChild(li);
                    }});
                }} else {{
                    commentsContent.innerHTML = '<li style="list-style: none; color: var(--text-muted);">No representative comments available for this category.</li>';
                }}
            }}
            
            // Initial comments render (first category)
            if (catLabels.length > 0) {{
                renderComments(catLabels[0]);
            }}

            // 7. Executive Recommendations (Top 3)
            const rankedCats = [...catLabels].sort((a, b) => distributions.category[b].Count - distributions.category[a].Count);
            const CAT_REC_TEMPLATES = {{
                'App Bug': {{
                    title: 'App Bug Fixes',
                    recommendation: 'Focus engineering effort on crash reports, payment flow stability, and loading screen failures.',
                    color: '#d97706',
                    bg: '#fffbeb',
                    border: '#f59e0b',
                    text: '#451a03'
                }},
                'Delivery': {{
                    title: 'Courier SLAs',
                    recommendation: 'Review courier SLA compliance and delayed delivery hotspots.',
                    color: '#2563eb',
                    bg: '#eff6ff',
                    border: '#3b82f6',
                    text: '#1e3a8a'
                }},
                'Staff/Support': {{
                    title: 'Support Workflows',
                    recommendation: 'Audit customer support workflows, hold times, and response templates to improve compliance.',
                    color: '#10b981',
                    bg: '#f0fdf4',
                    border: '#10b981',
                    text: '#14532d'
                }},
                'Billing': {{
                    title: 'Billing & Refunds',
                    recommendation: 'Audit charge mechanisms, billing errors, and payment gateway double-deductions.',
                    color: '#7c3aed',
                    bg: '#f5f3ff',
                    border: '#7c3aed',
                    text: '#2e1065'
                }},
                'Other': {{
                    title: 'General UX & Features',
                    recommendation: 'Address general user experience suggestions, logo feedback, and minor feature requests.',
                    color: '#4b5563',
                    bg: '#f9fafb',
                    border: '#9ca3af',
                    text: '#1f2937'
                }}
            }};

            const spotlightContainer = document.getElementById('spotlight-container');
            rankedCats.slice(0, 3).forEach((cat, idx) => {{
                const tmpl = CAT_REC_TEMPLATES[cat] || CAT_REC_TEMPLATES['Other'];
                const pct = distributions.category[cat].Percentage;
                const card = document.createElement('div');
                card.className = 'spotlight-card';
                card.style.backgroundColor = tmpl.bg;
                card.style.borderLeft = `5px solid ${{tmpl.border}}`;
                
                card.innerHTML = `
                    <div class="spotlight-priority" style="color: ${{tmpl.color}};">Priority ${{idx + 1}}</div>
                    <div class="spotlight-title" style="color: var(--text-main);">${{cat}} (${{pct}}%)</div>
                    <div class="spotlight-desc" style="color: ${{tmpl.text}};">
                        <strong>Recommendation:</strong> ${{tmpl.recommendation}}
                    </div>
                `;
                spotlightContainer.appendChild(card);
            }});

            // 8. Detailed Technical Recommendations
            const recsContainer = document.getElementById('recs-container');
            recommendations.forEach(rec => {{
                const impactClass = rec.impact.toLowerCase();
                const card = document.createElement('div');
                card.className = `rec-card ${{impactClass}}`;
                
                card.innerHTML = `
                    <div class="rec-header">
                        <span class="badge badge-${{impactClass}}">${{rec.impact}} Impact</span>
                        <h4>${{rec.title}}</h4>
                    </div>
                    <p class="rec-desc">${{rec.description}}</p>
                `;
                recsContainer.appendChild(card);
            }});
            
            // Sync with theme immediately if dark mode is active on system
            updateChartThemes();
        }});
    </script>
</body>
</html>
"""
    return html
