import os
import json
import re
import pandas as pd
import urllib.request
import urllib.error
import time
from dotenv import load_dotenv  # type: ignore[import-untyped]

# Load environment variables from .env file
load_dotenv()

from src import config

# Try importing SDKs dynamically
GEMINI_AVAILABLE = False
OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai  # type: ignore[import-untyped]
    GEMINI_AVAILABLE = True
except ImportError:
    pass

try:
    from openai import OpenAI  # type: ignore[import-untyped]
    OPENAI_AVAILABLE = True
except ImportError:
    pass

# Track API state globally
API_STATUS = "Local Heuristic Classifier (Offline Mode)"
CLIENT_MODEL = "Local Classification Engine"
API_CIRCUIT_BROKEN = False

def reset_api_circuit():
    """
    Resets the AI API circuit breaker to allow new API attempts.
    """
    global API_CIRCUIT_BROKEN
    API_CIRCUIT_BROKEN = False

def configure_apis():
    """
    Configures the AI clients depending on env keys.
    Sets global API status tags.
    """
    global API_STATUS, CLIENT_MODEL
    
    if API_CIRCUIT_BROKEN:
        API_STATUS = "Local Heuristic Classifier (Offline Mode)"
        CLIENT_MODEL = "Local Classification Engine"
        return "mock"
    
    # Check Groq first
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        API_STATUS = "Groq API Active"
        CLIENT_MODEL = "llama-3.3-70b-versatile"
        return "groq"
    
    # Check Gemini second
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and GEMINI_AVAILABLE:
        try:
            genai.configure(api_key=gemini_key)
            # Test model configuration
            _ = genai.GenerativeModel('gemini-2.0-flash')
            API_STATUS = "Gemini API Active"
            CLIENT_MODEL = "gemini-2.0-flash"
            return "gemini"
        except Exception:
            pass

    # Check OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key and OPENAI_AVAILABLE:
        try:
            # Simple instantiation test
            _ = OpenAI(api_key=openai_key)
            API_STATUS = "OpenAI API Active"
            CLIENT_MODEL = "gpt-3.5-turbo"
            return "openai"
        except Exception:
            pass
            
    API_STATUS = "Local Heuristic Classifier (Offline Mode)"
    CLIENT_MODEL = "Local Classification Engine"
    return "mock"

# Run initial config
active_provider = configure_apis()

def get_api_status():
    """
    Returns the current active AI client status.
    """
    configure_apis()
    return {
        "status": API_STATUS,
        "model": CLIENT_MODEL
    }

def mock_classify(text, rating=None):
    """
    Rule-based mock classifier that runs locally if no LLM credentials exist.
    """
    text_lower = text.lower().strip()
    
    # 1. CATEGORY DETECTION
    category_scores = {cat: 0 for cat in config.ALLOWED_CATEGORIES}
    for cat, keywords in config.MOCK_CATEGORY_RULES.items():
        for kw in keywords:
            if kw in text_lower:
                category_scores[cat] += 1
                
    best_cat = max(category_scores, key=category_scores.get)
    if category_scores[best_cat] == 0:
        best_cat = "Other"
        
    # 2. SENTIMENT DETECTION
    pos_score = sum(1 for kw in config.MOCK_SENTIMENT_RULES['Positive'] if kw in text_lower)
    neg_score = sum(1 for kw in config.MOCK_SENTIMENT_RULES['Negative'] if kw in text_lower)
    
    rating_val = None
    if pd.notna(rating):
        try:
            rating_val = float(rating)
        except ValueError:
            pass
            
    # Base text sentiment
    text_sentiment = None
    if pos_score > neg_score:
        text_sentiment = "Positive"
    elif neg_score > pos_score:
        text_sentiment = "Negative"
    else:
        text_sentiment = "Neutral"
        
    # Final sentiment logic
    if rating_val is not None:
        if rating_val >= 4.0:
            # Sarcasm check: rating is high, but negative keywords outweigh positive keywords
            if neg_score > pos_score:
                sentiment = "Negative"
            else:
                sentiment = "Positive"
        elif rating_val <= 2.0:
            # Mismatch check: rating is low, but positive keywords outweigh negative keywords
            if pos_score > neg_score:
                sentiment = "Positive"
            else:
                sentiment = "Negative"
        else:
            # Rating is 3.0 (Neutral)
            if text_sentiment != "Neutral":
                sentiment = text_sentiment
            else:
                sentiment = "Neutral"
    else:
        # No rating: follow text sentiment
        sentiment = text_sentiment
            
    # 3. CONFIDENCE ESTIMATOR
    confidence = 0.85
    # Sarcasm / Rating mismatch reduces confidence
    if rating_val is not None:
        if rating_val >= 4.0 and sentiment == "Negative":
            confidence = 0.45
        elif rating_val <= 2.0 and sentiment == "Positive":
            confidence = 0.50
    # Absence of rating reduces confidence slightly
    else:
        confidence -= 0.10
        
    # Ambiguous keywords reduce confidence
    if pos_score > 0 and neg_score > 0:
        confidence -= 0.15
        
    confidence = max(0.3, min(0.99, round(confidence, 2)))
    
    # 4. ISSUE SUMMARY GENERATOR
    # Build a clean one-line summary
    summary = text
    # Strip common noise prefixes to create a summary
    summary_clean = re.sub(r'(?i)^(i was charged|cannot add|login button|login keeps|app crashed|app stuck|driver could not|waited two hours|order mark|food was spilled|customer care)\b', '', summary).strip()
    if summary_clean and len(summary_clean) > 5:
        summary = text[:1].upper() + text[1:] # Capitalize first letter
    
    # Truncate to make it a neat one-line summary
    if len(summary) > 60:
        summary = summary[:57] + "..."
        
    return {
        "sentiment": sentiment,
        "category": best_cat,
        "summary": summary,
        "confidence": confidence
    }

def query_gemini(text, rating=None):
    """
    Queries Google Gemini for structured analysis.
    """
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    rating_str = f"Rating: {rating}/5" if pd.notna(rating) else "Rating: Missing"
    prompt = f"""
    Analyze the following customer feedback text from a food and grocery delivery app.
    
    Feedback: "{text}"
    {rating_str}
    
    Generate a JSON object containing:
    1. "sentiment": Strictly choose one of: ["Positive", "Neutral", "Negative"]. Evaluate sentiment from the text. Note: High ratings with negative text (e.g. rating 5 but complaining about app crashing) indicate sarcasm/error; classify the actual text sentiment (e.g. Negative).
    2. "category": Strictly choose one of: ["Billing", "App Bug", "Delivery", "Staff/Support", "Other"].
       - Billing: covers payments, refunds, duplicate charges, billing, fees, coupon issues.
       - App Bug: covers app crashes, freezes, loading loops, login issues, map screen errors.
       - Delivery: covers late delivery, cold food, spilled items, wrong drop-off, courier behavior.
       - Staff/Support: covers customer care, support agent issues, no response from emails/chat.
       - Other: covers general comments, feature requests, generic feedback.
    3. "summary": A concise one-line business-friendly summary of the complaint.
    4. "confidence": A float value between 0.0 and 1.0 expressing your classification confidence. Reduce confidence if text is ambiguous or contradicts the rating.
    
    Respond STRICTLY in JSON format matching this JSON schema:
    {{
      "sentiment": "string",
      "category": "string",
      "summary": "string",
      "confidence": float
    }}
    Do not add any markup, tags, or markdown fences. Just the raw JSON.
    """
    
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    return json.loads(response.text.strip())

def query_openai(text, rating=None):
    """
    Queries OpenAI for structured analysis.
    """
    client = OpenAI()
    rating_str = f"Rating: {rating}/5" if pd.notna(rating) else "Rating: Missing"
    
    prompt = f"""
    Analyze this feedback and output JSON.
    Feedback: "{text}"
    {rating_str}
    
    Categories: ["Billing", "App Bug", "Delivery", "Staff/Support", "Other"]
    Sentiments: ["Positive", "Neutral", "Negative"]
    
    Output JSON schema:
    {{
      "sentiment": "Positive" | "Neutral" | "Negative",
      "category": "Billing" | "App Bug" | "Delivery" | "Staff/Support" | "Other",
      "summary": "one-line summary",
      "confidence": float
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a data analyzer. Only output valid JSON matching the schema."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content.strip())

def query_groq(text, rating=None):
    """
    Queries Groq API via urllib for structured analysis with retry backoff for rate limits.
    """
    groq_key = os.environ.get("GROQ_API_KEY")
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    rating_str = f"Rating: {rating}/5" if pd.notna(rating) else "Rating: Missing"
    
    prompt = f"""
    Analyze the following customer feedback text from a food and grocery delivery app.
    
    Feedback: "{text}"
    {rating_str}
    
    Generate a JSON object containing:
    1. "sentiment": Strictly choose one of: ["Positive", "Neutral", "Negative"]. Base this strictly on text tone. Sarcasm must be classified as Negative. Polite feature/restaurant requests (e.g. "please add vegan food") without negative sentiment should be Neutral.
    2. "category": Strictly choose one of: ["Billing", "App Bug", "Delivery", "Staff/Support", "Other"].
       - Billing: covers payment gateway failures, refund delay, duplicate charges, service fees, coupons (like SAVE50) not applying.
       - App Bug: covers app crashes, freezes, loading loops, login button unresponsive, battery drain, address save button greyed out.
       - Delivery: covers late delivery, cold food, spilled items, order delivered to wrong address, courier/driver behavior.
       - Staff/Support: covers customer care hold time, support agents (e Priya/Meera/Rahul) unresponsive, no reply to emails/chats.
       - Other: covers general suggestions, feature requests (e.g. adding restaurant types), generic comments ("it is okay").
    3. "summary": A concise business-focused summary of the issue (strictly under 8 words). Use active voice and focus on the technical or operational root cause. Do NOT use filler words like "Customer says..." or "User complains about...". Strip raw order IDs and agent names.
       - Example: "SAVE50 coupon checkout failure", "App freezes on address save", "Spilled order delivery", "Support email response delay".
    4. "confidence": A float value between 0.0 and 1.0 expressing your classification confidence. Reduce confidence if text is ambiguous or contradicts the rating.
    
    Respond STRICTLY in JSON format matching this JSON schema:
    {{
      "sentiment": "string",
      "category": "string",
      "summary": "string",
      "confidence": float
    }}
    Do not add any markup, tags, or markdown fences. Just the raw JSON.
    """
    
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a customer feedback analyzer. Output raw, valid JSON only, matching the requested schema."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0
    }
    
    # Implementing request retry logic with exponential backoff for HTTP 429
    max_retries = 1
    backoff = 1.0
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(data).encode("utf-8"), 
                headers=headers, 
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                content = res_json["choices"][0]["message"]["content"].strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                return json.loads(content.strip())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2.0
                continue
            else:
                raise e

def analyze_feedback(text, rating=None):
    """
    Main entry point for AI enrichment. Routes the request to the active provider
    and falls back safely if any API call crashes.
    """
    provider = configure_apis()
    
    if provider == "mock":
        return mock_classify(text, rating)
        
    try:
        # Avoid hit rate limit triggers by adding a tiny delay
        if provider == "groq":
            time.sleep(0.15)
            return query_groq(text, rating)
        elif provider == "gemini":
            return query_gemini(text, rating)
        elif provider == "openai":
            return query_openai(text, rating)
    except Exception as e:
        # Safe fallback in case of rate limits, network loss, or schema errors
        global API_CIRCUIT_BROKEN
        API_CIRCUIT_BROKEN = True
        
        fallback_res = mock_classify(text, rating)
        fallback_res["confidence"] = min(fallback_res["confidence"], 0.6) # Penalty for LLM crash
        return fallback_res

def query_groq_batch(batch_rows):
    """
    Queries Groq API via urllib to process a list of feedback records in one API call.
    """
    groq_key = os.environ.get("GROQ_API_KEY")
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    # Format the input records for the LLM
    records_to_analyze = []
    for row in batch_rows:
        records_to_analyze.append({
            "id": int(row["id"]),
            "text": str(row["feedback_text"]),
            "rating": float(row["rating"]) if pd.notna(row["rating"]) else None
        })
        
    prompt = f"""
    Analyze the following customer feedback records from a food and grocery delivery app.
    
    For each record, generate:
    1. "id": The input ID.
    2. "sentiment": Strictly choose one of: ["Positive", "Neutral", "Negative"]. Base this strictly on text tone. Sarcasm must be classified as Negative. Polite feature/restaurant requests (e.g. "please add vegan food") without negative sentiment should be Neutral.
    3. "category": Strictly choose one of: ["Billing", "App Bug", "Delivery", "Staff/Support", "Other"].
       - Billing: covers payment gateway failures, refund delay, duplicate charges, service fees, coupons (like SAVE50) not applying.
       - App Bug: covers app crashes, freezes, loading loops, login button unresponsive, battery drain, address save button greyed out.
       - Delivery: covers late delivery, cold food, spilled items, order delivered to wrong address, courier/driver behavior.
       - Staff/Support: covers customer care hold time, support agents (e Priya/Meera/Rahul) unresponsive, no reply to emails/chats.
       - Other: covers general suggestions, feature requests (e.g. adding restaurant types), generic comments ("it is okay").
    4. "summary": A concise business-focused summary of the issue (strictly under 8 words). Use active voice and focus on the technical or operational root cause. Do NOT use filler words like "Customer says..." or "User complains about...". Strip raw order IDs and agent names.
       - Example: "SAVE50 coupon checkout failure", "App freezes on address save", "Spilled order delivery", "Support email response delay".
    5. "confidence": A float value between 0.0 and 1.0 expressing your classification confidence. Reduce confidence if text is ambiguous or contradicts the rating.
    
    Here is the list of records to analyze:
    {json.dumps(records_to_analyze, indent=2)}
    
    Respond STRICTLY as a JSON object containing a single key "results" which is a list of JSON objects matching this schema:
    {{
      "results": [
        {{
          "id": int,
          "sentiment": "Positive" | "Neutral" | "Negative",
          "category": "Billing" | "App Bug" | "Delivery" | "Staff/Support" | "Other",
          "summary": "string",
          "confidence": float
        }},
        ...
      ]
    }}
    Do not add any markdown formatting fences or other text. Just output raw, valid JSON.
    """
    
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a customer feedback analyzer. Output raw, valid JSON only, matching the requested schema containing a list under 'results'."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0
    }
    
    # Call Groq API with retries
    max_retries = 1
    backoff = 1.0
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(data).encode("utf-8"), 
                headers=headers, 
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                response_content = res_json["choices"][0]["message"]["content"].strip()
                break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2.0
                continue
            else:
                raise e

    if not response_content:
        raise Exception("Empty response from Groq API")
        
    # Clean up formatting if any
    if response_content.startswith("```json"):
        response_content = response_content[7:]
    if response_content.endswith("```"):
        response_content = response_content[:-3]
        
    parsed = json.loads(response_content.strip())
    results_list = parsed.get("results", [])
    
    # Map results list back to origin row elements
    results_map = {int(res["id"]): res for res in results_list if "id" in res}
    
    mapped_results = []
    for row in batch_rows:
        row_id = int(row["id"])
        ai_res = results_map.get(row_id)
        if ai_res:
            mapped_results.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'source': row['source'],
                'rating': row['rating'],
                'feedback_text': row['feedback_text'],
                'normalized_text': row['normalized_text'],
                'complaint_count': row['complaint_count'],
                'ai_sentiment': ai_res.get('sentiment', 'Neutral'),
                'ai_category': ai_res.get('category', 'Other'),
                'ai_summary': ai_res.get('summary', row['feedback_text'][:50]),
                'ai_confidence': float(ai_res.get('confidence', 0.8))
            })
        else:
            # If a specific ID is missing in response, fall back to row heuristic
            fallback_res = mock_classify(row['feedback_text'], row['rating'])
            mapped_results.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'source': row['source'],
                'rating': row['rating'],
                'feedback_text': row['feedback_text'],
                'normalized_text': row['normalized_text'],
                'complaint_count': row['complaint_count'],
                'ai_sentiment': fallback_res.get('sentiment', 'Neutral'),
                'ai_category': fallback_res.get('category', 'Other'),
                'ai_summary': fallback_res.get('summary', row['feedback_text'][:50]),
                'ai_confidence': float(fallback_res.get('confidence', 0.8))
            })
            
    return mapped_results

def analyze_feedback_batch(batch_rows):
    """
    Enriches a batch of rows using the active provider's batch API if supported.
    Falls back to row-by-row analysis if not supported or if the batch call fails.
    """
    provider = configure_apis()
    if provider == "groq":
        try:
            return query_groq_batch(batch_rows)
        except Exception as e:
            # Safe fallback: run row-by-row on error
            global API_CIRCUIT_BROKEN
            API_CIRCUIT_BROKEN = True
            pass
            
    # Fallback to row-by-row enrichment
    results = []
    for row in batch_rows:
        ai_res = analyze_feedback(row['feedback_text'], row['rating'])
        results.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'source': row['source'],
            'rating': row['rating'],
            'feedback_text': row['feedback_text'],
            'normalized_text': row['normalized_text'],
            'complaint_count': row['complaint_count'],
            'ai_sentiment': ai_res.get('sentiment', 'Neutral'),
            'ai_category': ai_res.get('category', 'Other'),
            'ai_summary': ai_res.get('summary', row['feedback_text'][:50]),
            'ai_confidence': float(ai_res.get('confidence', 0.8))
        })
    return results
