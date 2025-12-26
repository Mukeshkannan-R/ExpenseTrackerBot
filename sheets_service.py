import requests

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyyYG9U0cg3D1-8nJ0MfB7jz-3kHo296DrLFaCpyL8F-7eDMBTEHezQUxpTvnYS0KM/exec"  # ← FILL LATER

def add_expense_row(date, amount, currency, category, note, user_id, username):
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