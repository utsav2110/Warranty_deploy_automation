import os
import requests

token = os.environ["EMAIL_TRIGGER_TOKEN"]
# trigger_url = f"https://your-app.streamlit.app/?trigger=email&token={token}"
trigger_url = f"http://localhost:8501/?trigger=email&token={token}"


r = requests.get(trigger_url)
if r.status_code == 200:
    print("✅ Email triggered successfully")
else:
    print(f"❌ Failed to trigger email: {r.status_code} - {r.text}")