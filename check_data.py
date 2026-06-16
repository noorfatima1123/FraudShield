import json
from pathlib import Path

# Check Phase 3 data exists
phase3_users = Path('phase3-semantic-memory/embeddings/user_embeddings.json')
phase3_vendors = Path('phase3-semantic-memory/embeddings/vendor_embeddings.json')
phase2_transactions = Path('phase2-preprocessing/cleaned_data/real_transactions_test_cleaned.json')

print('='*50)
print('CHECKING DATA FILES')
print('='*50)

if phase3_users.exists():
    size = phase3_users.stat().st_size / 1024 / 1024
    print(f'User embeddings: YES ({size:.1f} MB)')
else:
    print('User embeddings: MISSING')

if phase3_vendors.exists():
    size = phase3_vendors.stat().st_size / 1024 / 1024
    print(f'Vendor embeddings: YES ({size:.1f} MB)')
else:
    print('Vendor embeddings: MISSING')

if phase2_transactions.exists():
    print(f'Test transactions: YES')
    with open(phase2_transactions, 'r') as f:
        lines = sum(1 for _ in f)
    print(f'  Total test transactions: {lines}')
else:
    print('Test transactions: MISSING')

print('\n✅ Check complete!')