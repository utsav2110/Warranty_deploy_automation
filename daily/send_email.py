import os
import requests
import urllib.parse


token = os.environ["EMAIL_TRIGGER_TOKEN"]
# encoded_token = urllib.parse.quote(token)
trigger_url = f"https://warranty-tracking-system.streamlit.app/?trigger=email&token={token}"
r = requests.get(trigger_url)
if r.status_code == 200:
    print("✅ Email triggered successfully")
else:
    print(f"❌ Failed to trigger email: {r.status_code} - {r.text}")
