import csv
import hashlib
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None

RAW_DIR = Path('real_data/raw')
OUTPUT_DIR = Path('real_data/output')
RAW_FILE = RAW_DIR / 'creditcard.csv'
TRANSACTIONS_FILE = OUTPUT_DIR / 'transactions.json'
STATS_FILE = OUTPUT_DIR / 'dataset_stats.json'
BATCH_SIZE = 10_000
DEFAULT_SAMPLE_SIZE = 50_000
TOTAL_WINDOW_DAYS = 30


def stable_hash(value: str) -> int:
    digest = hashlib.sha256(value.encode('utf-8')).hexdigest()
    return int(digest, 16)


def deterministic_id(prefix: str, values: List[str]) -> str:
    combined = ''.join(values)
    return f"{prefix}_{stable_hash(combined)}"


def parse_row(row: Dict[str, str]) -> Dict[str, object]:
    transaction_id = row.get('TransactionID') or row.get('transaction_id')
    amount = row.get('Amount')
    class_label = row.get('Class') or row.get('class') or row.get('LABEL')

    if amount is None or class_label is None:
        raise ValueError('Missing required Amount or Class column in input row.')

    return {
        'amount': float(amount),
        'is_fraud': int(class_label),
        'features': {f'V{i}': float(row[f'V{i}']) for i in range(1, 29)},
        'transaction_id': transaction_id,
    }


def generate_timestamp(row_index: int, total_rows: int, start_date: datetime) -> str:
    total_seconds = TOTAL_WINDOW_DAYS * 24 * 3600
    interval = total_seconds / max(total_rows, 1)
    offset_seconds = int(interval * row_index + random.uniform(0, min(interval, 600)))
    return (start_date + timedelta(seconds=offset_seconds)).isoformat() + 'Z'


def load_csv_in_chunks(path: Path, chunk_size: int, max_rows: Optional[int] = None) -> Iterable[List[Dict[str, str]]]:
    with path.open('r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        batch: List[Dict[str, str]] = []
        for index, row in enumerate(reader, start=1):
            batch.append(row)
            if max_rows is not None and index >= max_rows:
                yield batch
                return
            if len(batch) >= chunk_size:
                yield batch
                batch = []
        if batch:
            yield batch


def count_rows(path: Path) -> int:
    with path.open('r', encoding='utf-8') as csvfile:
        return sum(1 for _ in csvfile) - 1


def build_transactions(
    max_rows: Optional[int] = None,
    chunk_size: int = BATCH_SIZE,
) -> Dict[str, int]:
    if not RAW_FILE.exists():
        raise FileNotFoundError(f'Raw dataset file not found: {RAW_FILE}')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_rows = count_rows(RAW_FILE)
    requested_rows = min(max_rows, total_rows) if max_rows is not None else total_rows
    start_date = datetime.utcnow() - timedelta(days=TOTAL_WINDOW_DAYS)

    stats = {
        'total_rows_available': total_rows,
        'rows_processed': 0,
        'fraud_count': 0,
        'non_fraud_count': 0,
        'sample_size': requested_rows,
        'start_date': start_date.isoformat() + 'Z',
        'end_date': (start_date + timedelta(days=TOTAL_WINDOW_DAYS)).isoformat() + 'Z',
    }

    progress = tqdm(total=requested_rows, unit='rows', desc='Processing transactions') if tqdm else None
    first_record = True

    with TRANSACTIONS_FILE.open('w', encoding='utf-8') as writer:
        writer.write('[\n')

        processed = 0
        for batch in load_csv_in_chunks(RAW_FILE, chunk_size, max_rows=requested_rows):
            for row in batch:
                parsed = parse_row(row)
                index = processed + 1
                user_id = deterministic_id('USER', [row['V1'], row['V2'], row['V3']])
                vendor_id = deterministic_id('VENDOR', [row['V4'], row['V5'], row['V6']])
                transaction_id = f'TX_{index:08d}'
                timestamp = generate_timestamp(index - 1, requested_rows, start_date)

                transaction = {
                    'transaction_id': transaction_id,
                    'amount': parsed['amount'],
                    'user_id': user_id,
                    'vendor_id': vendor_id,
                    'timestamp': timestamp,
                    'payment_method': 'credit_card',
                    'is_fraud': parsed['is_fraud'],
                    **parsed['features'],
                }

                stats['rows_processed'] += 1
                if parsed['is_fraud'] == 1:
                    stats['fraud_count'] += 1
                else:
                    stats['non_fraud_count'] += 1

                if not first_record:
                    writer.write(',\n')
                writer.write(json.dumps(transaction, ensure_ascii=False))
                first_record = False
                processed += 1
                if progress:
                    progress.update(1)

        writer.write('\n]\n')

    if progress:
        progress.close()

    stats['fraud_ratio'] = round(stats['fraud_count'] / max(stats['rows_processed'], 1), 6)
    stats['non_fraud_ratio'] = round(stats['non_fraud_count'] / max(stats['rows_processed'], 1), 6)

    with STATS_FILE.open('w', encoding='utf-8') as stats_writer:
        json.dump(stats, stats_writer, indent=2)

    return stats


def main(sample_size: Optional[int] = DEFAULT_SAMPLE_SIZE) -> None:
    print(f'Loading dataset from {RAW_FILE}')
    print(f'Writing output to {TRANSACTIONS_FILE} and {STATS_FILE}')
    stats = build_transactions(max_rows=sample_size)
    print('Completed processing.')
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load credit card fraud CSV into FraudShield JSON format.')
    parser.add_argument('--sample-size', type=int, default=DEFAULT_SAMPLE_SIZE, help='Number of rows to process for testing. Use 0 or negative to process all rows.')
    args = parser.parse_args()

    sample = args.sample_size if args.sample_size > 0 else None
    try:
        main(sample_size=sample)
    except Exception as exc:
        print(f'Error: {exc}')
        raise
