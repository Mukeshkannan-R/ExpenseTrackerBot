# sheets_service.py - 12-HOUR TIME FORMAT (1 PM, 2 PM, etc.)
import requests
import os
from datetime import datetime

WEBHOOK_URL = os.getenv('https://script.google.com/macros/s/AKfycby4BVJDm0dPonvltqil0Wtqo0ABLs0_dXrhoThhcAA_VHUrPCrg2uPsRMiyOwwDIN4/exec')

def add_expense_row(date, amount, currency, category, note, user_id, username):
    if not WEBHOOK_URL:
        print("❌ GOOGLE_SHEETS_WEBHOOK not set!")
        return False
        
    # Generate 12-Hour Timestamp (1:30 PM IST format)
    timestamp = datetime.now().strftime("%I:%M %p IST")  # "09:09 PM IST"
    
    payload = {
        "date": date,
        "amount": amount,
        "currency": currency,
        "category": category,
        "note": note,
        "user_id": user_id,
        "username": username,
        "timestamp": timestamp  # ← NEW: 12-hour format
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"Sheet response: {response.status_code} | Time: {timestamp}")
        return response.status_code == 200
    except Exception as e:
        print(f"Sheet error: {e}")
        return False