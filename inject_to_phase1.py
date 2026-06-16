import json
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

print("Loading transactions...")
input_path = Path("real_data/output/transactions.json")
with open(input_path, 'r') as f:
    transactions = json.load(f)

print(f"Loaded {len(transactions)} transactions")

# Convert to Phase 1 format
phase1_transactions = []
for tx in tqdm(transactions, desc="Converting"):
    phase1_tx = {
        "transaction_id": tx["transaction_id"],
        "amount": float(tx["amount"]),
        "currency": "USD",
        "sender_id": tx["user_id"],
        "receiver_id": tx["vendor_id"],
        "timestamp": tx["timestamp"],
        "payment_method": "credit_card",
        "status": "flagged" if tx["is_fraud"] == 1 else "completed",
        "is_fraud": tx["is_fraud"],
        "_source": "real_creditcard_data",
        "_ingestion_timestamp": datetime.utcnow().isoformat() + "Z"
    }
    phase1_transactions.append(phase1_tx)

# Split into train/test (80/20)
split_idx = int(len(phase1_transactions) * 0.8)
train_data = phase1_transactions[:split_idx]
test_data = phase1_transactions[split_idx:]

# Save to Phase 1 data folder
output_dir = Path("phase1-data-ingestion/data")
output_dir.mkdir(parents=True, exist_ok=True)

with open(output_dir / "real_transactions_train.json", "w") as f:
    json.dump(train_data, f, indent=2)

with open(output_dir / "real_transactions_test.json", "w") as f:
    json.dump(test_data, f, indent=2)

print(f"\n✅ Saved {len(train_data)} training transactions")
print(f"✅ Saved {len(test_data)} test transactions")
print(f"\n📁 Location: {output_dir}")