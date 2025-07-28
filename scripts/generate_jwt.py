"""
Utility to generate a JWT token for the current session using the ANOMALY_JWT_SECRET.
Run this script and copy the output token to your Streamlit dashboard or .env file.
"""
import os
import jwt
import datetime

SECRET = os.environ.get("ANOMALY_JWT_SECRET", "dev_secret")
USER = os.environ.get("ANOMALY_JWT_USER", "test-user")
EXPIRE_HOURS = int(os.environ.get("ANOMALY_JWT_EXPIRE_HOURS", 751))
print(EXPIRE_HOURS)
payload = {
    "sub": USER,
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=EXPIRE_HOURS)
}
token = jwt.encode(payload, SECRET, algorithm="HS256")
print(token)
