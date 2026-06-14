import os

# Allowed categories and sentiments
ALLOWED_CATEGORIES = ['Billing', 'App Bug', 'Delivery', 'Staff/Support', 'Other']
ALLOWED_SENTIMENTS = ['Positive', 'Neutral', 'Negative']

# Category mapping lookup for the validation layer
CATEGORY_FALLBACK_MAP = {
    'payment issue': 'Billing',
    'refund': 'Billing',
    'subscription': 'Billing',
    'charge': 'Billing',
    'price': 'Billing',
    'fee': 'Billing',
    'payment': 'Billing',
    'billing': 'Billing',
    
    'technical error': 'App Bug',
    'crash': 'App Bug',
    'login': 'App Bug',
    'loading': 'App Bug',
    'button': 'App Bug',
    'battery': 'App Bug',
    'app': 'App Bug',
    
    'driver': 'Delivery',
    'livreur': 'Delivery',
    'late': 'Delivery',
    'cold food': 'Delivery',
    'delivery': 'Delivery',
    'food spilled': 'Delivery',
    'order late': 'Delivery',
    
    'support agent': 'Staff/Support',
    'customer care': 'Staff/Support',
    'no reply': 'Staff/Support',
    'support': 'Staff/Support',
    'agent': 'Staff/Support'
}

# Dataset Health Score Penalties (Deducted per 1% of affected records)
HEALTH_PENALTY_MISSING_TIMESTAMP = 1.0
HEALTH_PENALTY_MISSING_RATING = 0.5
HEALTH_PENALTY_DUPLICATE_ROW = 0.5
HEALTH_PENALTY_DUPLICATE_FEEDBACK = 1.0
HEALTH_PENALTY_EMPTY_FEEDBACK = 1.5
HEALTH_PENALTY_INVALID_TIMESTAMP = 1.0

# Mock LLM Rule-based Fallback Keywords
MOCK_SENTIMENT_RULES = {
    'Negative': [
        'crash', 'fail', 'cancel', 'delay', 'late', 'rude', 'worst', 'charge', 'refund', 
        'double', 'cierra', 'bura', 'impoli', 'cold', 'drains', 'battery', 'greyed', 
        'error', 'failed', 'subscription', 'ridiculous', 'hold', 'disconnected', 
        'miserable', 'slow', 'spill', 'empty', 'missing', 'bad', 'wrong',
        'fee', 'bill', 'charging', 'charged', 'debited', 'deducted', 'deduct', 'stuck', 
        'freeze', 'freezes', 'crashed', 'waiting', 'waited', 'hours', 'minutes', 'spilled', 
        'broken', 'incomplete', 'unauthorized', 'unapproved', 'scam', 'cheat', 'cheated', 
        'complaint', 'issue', 'problem', 'terrible', 'awful', 'horrible', 'annoying', 'poor', 'unsatisfied',
        'nothing', 'never', 'none', 'no', 'not'
    ],
    'Positive': [
        'great', 'love', 'good', 'perfect', 'fantastic', 'wonderful', 'helpful', 'friendly', 
        'solved', 'merci', 'excelente', 'encanta', 'super', 'smooth', 'brilliant', 'fast', 'quick',
        'thank', 'thanks', 'appreciate', 'happy', 'satisfied', 'well', 'nice', 'excellent', 'awesome', 'best'
    ]
}

MOCK_CATEGORY_RULES = {
    'Billing': [
        'charge', 'billing', 'refund', 'deduct', 'double', 'money', 'subscription', 'card', 
        'payment', 'fee', 'invoice', 'price', 'cost', 'pay', 'coupon', 'promo', 'save50', 
        'deduction', 'debited'
    ],
    'App Bug': [
        'app', 'crash', 'loading', 'freeze', 'screen', 'button', 'greyed', 'save', 'login', 
        'battery', 'update', 'version', 'cierra', 'aplicacion', 'bug', 'battery', 'loading', 
        'login', 'slow', 'freezes'
    ],
    'Delivery': [
        'delivery', 'driver', 'late', 'delay', 'cold', 'food', 'door', 'wrong', 'spill', 
        'bag', 'arrive', 'courier', 'livreur', 'delivered', 'address'
    ],
    'Staff/Support': [
        'agent', 'support', 'customer', 'care', 'priya', 'meera', 'vikram', 'rahul', 'sana', 
        'anil', 'neha', 'arjun', 'reply', 'email', 'chat', 'representative', 'hold'
    ]
}
