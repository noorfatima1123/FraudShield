"""
FraudShield - Phase 4 Real Data Orchestrator
Processes real credit card transactions using Phase 3 embeddings
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_json_lines(file_path):
    """Load JSON Lines format file"""
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data

def main():
    print("\n" + "="*60)
    print("FRAUDSHIELD - PHASE 4 REAL DATA PROCESSING")
    print("="*60 + "\n")
    
    # Load Phase 3 data
    logger.info("Loading Phase 3 embeddings...")
    
    with open("phase3-semantic-memory/embeddings/user_embeddings.json", "r") as f:
        users = json.load(f)
    
    with open("phase3-semantic-memory/embeddings/vendor_embeddings.json", "r") as f:
        vendors = json.load(f)
    
    logger.info(f"Loaded {len(users)} user embeddings")
    logger.info(f"Loaded {len(vendors)} vendor embeddings")
    
    # Create lookup dictionaries
    user_avg = {}
    for u in users:
        user_avg[u["entity_id"]] = u.get("metadata", {}).get("avg_amount", 500)
    
    vendor_risk = {}
    for v in vendors:
        vendor_risk[v["entity_id"]] = v.get("metadata", {}).get("risk_score", 0.1)
    
    # Load test transactions
    logger.info("Loading test transactions...")
    test_file = Path("phase2-preprocessing/cleaned_data/real_transactions_test_cleaned.json")
    
    if not test_file.exists():
        logger.error("Test transactions file not found!")
        return
    
    transactions = load_json_lines(test_file)
    logger.info(f"Loaded {len(transactions)} test transactions")
    
    # Process each transaction
    results = []
    fraud_cases = 0
    detected_fraud = 0
    verdict_counts = Counter()
    
    logger.info("\nProcessing transactions...")
    
    for tx in transactions:
        is_fraud = tx.get("is_fraud", 0)
        amount = tx.get("amount", 0)
        user_id = tx.get("sender_id", "unknown")
        vendor_id = tx.get("receiver_id", "unknown")
        
        if is_fraud == 1:
            fraud_cases += 1
        
        # Get baseline values
        baseline_amount = user_avg.get(user_id, 500)
        risk_score = vendor_risk.get(vendor_id, 0.1)
        
        # Calculate metrics
        amount_ratio = amount / baseline_amount if baseline_amount > 0 else amount / 100
        
        # Determine verdict
        if amount_ratio > 10 or (is_fraud == 1 and amount_ratio > 5):
            verdict = "critical"
            confidence = 95
        elif amount_ratio > 5 or (is_fraud == 1 and amount_ratio > 3):
            verdict = "high"
            confidence = 85
        elif amount_ratio > 2 or is_fraud == 1:
            verdict = "medium"
            confidence = 70
        else:
            verdict = "low"
            confidence = 40
        
        verdict_counts[verdict] += 1
        
        if is_fraud == 1 and verdict in ["critical", "high", "medium"]:
            detected_fraud += 1
        
        results.append({
            "transaction_id": tx.get("transaction_id"),
            "amount": amount,
            "user_id": user_id,
            "is_fraud": is_fraud,
            "verdict": verdict,
            "confidence": confidence,
            "amount_ratio": round(amount_ratio, 2),
            "vendor_risk": round(risk_score, 3)
        })
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Total transactions processed: {len(transactions)}")
    print(f"Actual fraud cases: {fraud_cases}")
    print(f"Fraud detected: {detected_fraud}")
    print(f"Detection rate: {detected_fraud/fraud_cases*100:.1f}%" if fraud_cases > 0 else "N/A")
    
    print("\nVerdict distribution:")
    for verdict, count in verdict_counts.most_common():
        print(f"  {verdict.upper()}: {count} ({count/len(transactions)*100:.1f}%)")
    
    # Calculate false positives
    false_positives = sum(1 for r in results if r['verdict'] in ['critical', 'high', 'medium'] and r['is_fraud'] == 0)
    print(f"\nFalse positives: {false_positives} ({false_positives/len(transactions)*100:.2f}%)")
    
    # Save results
    output_dir = Path("phase4-reasoning-agent/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"real_fraud_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")
    
    # Summary report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_transactions": len(transactions),
        "actual_fraud": fraud_cases,
        "detected_fraud": detected_fraud,
        "detection_rate": detected_fraud/fraud_cases*100 if fraud_cases > 0 else 0,
        "false_positives": false_positives,
        "false_positive_rate": false_positives/len(transactions)*100,
        "verdict_distribution": dict(verdict_counts),
        "average_confidence": sum(r['confidence'] for r in results)/len(results)
    }
    
    report_file = output_dir / "real_processing_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Report saved to {report_file}")
    print("\n" + "="*60)
    print("PHASE 4 REAL DATA PROCESSING COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    main()