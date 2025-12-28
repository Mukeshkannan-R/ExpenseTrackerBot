import requests
import os

WEBHOOK_URL = os.getenv('https://script.google.com/macros/s/AKfycby4BVJDm0dPonvltqil0Wtqo0ABLs0_dXrhoThhcAA_VHUrPCrg2uPsRMiyOwwDIN4/exec')  # From Render env vars

def add_expense_row(date, amount, currency, category, note, user_id, username):
    if not WEBHOOK_URL:
        print("❌ WEBHOOK_URL not set!")
        return False
        
    payload = {
        "date": date,
        "amount": amount,
        "currency": currency,
        "category": category,
        "note": note,
        "user_id": user_id,
        "username": username
    }
    response = requests.post(WEBHOOK_URL, json=payload)
    print(f"Sheet response: {response.status_code}")
    return response.status_code == 200