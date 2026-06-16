import argparse
import json
from pathlib import Path
from typing import Dict, Any


def parse_amount(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_transactions(input_path: Path) -> list[dict]:
    if not input_path.exists():
        raise FileNotFoundError(f'Input file not found: {input_path}')

    transactions: list[dict] = []
    with input_path.open('r', encoding='utf-8') as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                transactions.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f'Invalid JSON on line {line_number}: {exc}') from exc

    return transactions


def extract_entities(transactions: list[dict]) -> tuple[list[dict], list[dict]]:
    users: Dict[str, dict] = {}
    vendors: Dict[str, dict] = {}

    for tx in transactions:
        amount = parse_amount(tx.get('amount', 0))

        user_id = tx.get('sender_id')
        if user_id:
            if user_id not in users:
                users[user_id] = {
                    'user_id': user_id,
                    'total_transactions': 0,
                    'total_amount': 0.0,
                    'avg_amount': 0.0,
                    'fraud_count': 0,
                }

            users[user_id]['total_transactions'] += 1
            users[user_id]['total_amount'] += amount
            if tx.get('is_fraud') == 1:
                users[user_id]['fraud_count'] += 1

        vendor_id = tx.get('receiver_id')
        if vendor_id:
            if vendor_id not in vendors:
                vendors[vendor_id] = {
                    'vendor_id': vendor_id,
                    'total_transactions': 0,
                    'total_amount': 0.0,
                    'risk_score': 0,
                }

            vendors[vendor_id]['total_transactions'] += 1
            vendors[vendor_id]['total_amount'] += amount

    for user in users.values():
        tx_count = user['total_transactions']
        user['avg_amount'] = user['total_amount'] / tx_count if tx_count > 0 else 0.0

    return list(users.values()), list(vendors.values())


def save_json(data: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def main(input_file: Path, output_dir: Path) -> None:
    print(f'Loading cleaned transactions from: {input_file}')
    transactions = load_transactions(input_file)
    print(f'Loaded {len(transactions)} transactions')

    users, vendors = extract_entities(transactions)

    users_output = output_dir / 'users_cleaned.json'
    vendors_output = output_dir / 'vendors_cleaned.json'

    save_json(users, users_output)
    save_json(vendors, vendors_output)

    print(f'✅ Saved {len(users)} users to {users_output}')
    print(f'✅ Saved {len(vendors)} vendors to {vendors_output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract users and vendors from cleaned transaction data.')
    parser.add_argument(
        '--input-file',
        type=Path,
        default=Path('phase2-preprocessing/cleaned_data/real_transactions_train_cleaned.json'),
        help='Path to the cleaned JSON lines transaction file',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('phase2-preprocessing/cleaned_data'),
        help='Directory to write users_cleaned.json and vendors_cleaned.json',
    )
    args = parser.parse_args()

    try:
        main(args.input_file, args.output_dir)
    except Exception as exc:
        print(f'Error: {exc}')
        raise
