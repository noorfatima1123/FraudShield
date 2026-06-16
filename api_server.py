"""
FraudShield - Real-time API Server
FastAPI backend for transaction fraud detection
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import random

# Load .env file
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="FraudShield API", description="Real-time fraud detection")

# Enable CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Phase 3 data
def load_embeddings():
    user_avg = {}
    vendor_risk = {}
    
    users_file = Path("phase3-semantic-memory/embeddings/user_embeddings.json")
    vendors_file = Path("phase3-semantic-memory/embeddings/vendor_embeddings.json")
    
    if users_file.exists():
        with open(users_file, 'r') as f:
            users = json.load(f)
            for u in users:
                user_avg[u["entity_id"]] = u.get("metadata", {}).get("avg_amount", 500)
    
    if vendors_file.exists():
        with open(vendors_file, 'r') as f:
            vendors = json.load(f)
            for v in vendors:
                vendor_risk[v["entity_id"]] = v.get("metadata", {}).get("risk_score", 0.1)
    
    return user_avg, vendor_risk

# Load data at startup
USER_AVG, VENDOR_RISK = load_embeddings()
print(f"Loaded {len(USER_AVG)} users, {len(VENDOR_RISK)} vendors")

class TransactionRequest(BaseModel):
    transaction_id: str
    amount: float
    user_id: str
    vendor_id: str
    timestamp: str
    payment_method: str = "credit_card"

class DetectionResponse(BaseModel):
    success: bool
    verdict: str
    confidence: int
    explanation: str
    actions: list
    alert_sent: bool

def send_email_alert(transaction_id, amount, user_id, verdict, confidence):
    """Send email alert via Gmail SMTP"""
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")
    
    if not sender or not password:
        print("Email not configured. Skipping...")
        return False
    
    subject = f"🚨 FRAUD ALERT: {verdict} Risk Transaction"
    
    body = f"""
    FRAUD ALERT DETECTED
    
    Transaction ID: {transaction_id}
    Amount: ${amount:,.2f}
    User ID: {user_id}
    Verdict: {verdict}
    Confidence: {confidence}%
    
    Actions Required: Immediate investigation recommended.
    
    Timestamp: {datetime.now().isoformat()}
    
    ---
    FraudShield Detection System
    """
    
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        
        print(f"✅ Email sent to {receiver}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

def analyze_transaction(transaction: TransactionRequest) -> DetectionResponse:
    """Analyze transaction and return verdict"""
    
    amount = transaction.amount
    user_id = transaction.user_id
    vendor_id = transaction.vendor_id
    
    # Parse time
    try:
        hour = int(transaction.timestamp.split(':')[0]) if ':' in transaction.timestamp else 12
    except:
        hour = 12
    
    # Get baseline
    baseline_amount = USER_AVG.get(user_id, 500)
    vendor_risk_score = VENDOR_RISK.get(vendor_id, 0.1)
    
    # Calculate ratio
    amount_ratio = amount / baseline_amount if baseline_amount > 0 else amount / 100
    
    # Time anomaly
    is_night = hour < 6 or hour > 22
    
    # Determine verdict
    if amount_ratio > 10 or (amount > 10000 and is_night):
        verdict = "CRITICAL"
        confidence = 95
        explanation = f"Amount ${amount:,.2f} is {amount_ratio:.1f}x higher than user average (${baseline_amount:,.2f}). Transaction at unusual hour."
    elif amount_ratio > 5 or amount > 5000:
        verdict = "HIGH"
        confidence = 85
        explanation = f"Amount ${amount:,.2f} exceeds normal pattern. User average: ${baseline_amount:,.2f}"
    elif amount_ratio > 2 or (amount > 1000 and is_night):
        verdict = "MEDIUM"
        confidence = 70
        explanation = f"Amount ${amount:,.2f} is moderately higher than usual."
    else:
        verdict = "LOW"
        confidence = 40
        explanation = f"Transaction amount ${amount:,.2f} is within normal range."
    
    # Add vendor risk to explanation
    if vendor_risk_score > 0.5:
        explanation += f" Vendor has high risk score ({vendor_risk_score:.2f})."
        if verdict == "MEDIUM":
            verdict = "HIGH"
            confidence += 10
    
    # Add night time warning
    if is_night and verdict != "LOW":
        explanation += " Transaction at unusual hour (3am)."
    
    # Actions based on verdict
    actions = []
    alert_sent = False
    
    if verdict in ["CRITICAL", "HIGH"]:
        actions.append("email_alert_sent")
        actions.append("added_to_review_queue")
        actions.append("case_created")
        alert_sent = send_email_alert(
            transaction.transaction_id, amount, user_id, verdict, confidence
        )
    elif verdict == "MEDIUM":
        actions.append("added_to_review_queue")
        actions.append("daily_digest_queued")
    else:
        actions.append("logged_only")
        actions.append("baseline_updated")
    
    return DetectionResponse(
        success=True,
        verdict=verdict,
        confidence=confidence,
        explanation=explanation,
        actions=actions,
        alert_sent=alert_sent
    )

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "users_loaded": len(USER_AVG), "vendors_loaded": len(VENDOR_RISK)}

@app.post("/api/detect", response_model=DetectionResponse)
async def detect_fraud(transaction: TransactionRequest):
    """Detect fraud for a single transaction"""
    try:
        result = analyze_transaction(transaction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    return {
        "total_users": len(USER_AVG),
        "total_vendors": len(VENDOR_RISK),
        "avg_user_amount": sum(USER_AVG.values()) / len(USER_AVG) if USER_AVG else 0
    }

if __name__ == "__main__":
    import uvicorn
    print("="*50)
    print("🚀 FraudShield API Server Starting...")
    print("="*50)
    uvicorn.run(app, host="0.0.0.0", port=5000)