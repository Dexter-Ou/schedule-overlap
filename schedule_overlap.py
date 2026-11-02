"""Read-only overlap check for explicitly offset CSV intervals. Python 3.10+."""
import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

MAX_BYTES = 2_000_000
MAX_ROWS = 2000
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})\Z')


def timestamp(value):
    if not STAMP.fullmatch(value):
        raise ValueError('timestamp must include seconds and Z or a numeric offset')
    if value.endswith('-00:00'):
        raise ValueError('unknown offset -00:00 is unsupported')
    if not value.endswith('Z') and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValueError('invalid numeric offset')
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(dt.timezone.utc)


def check(path):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('input exceeds byte limit')
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
    if reader.fieldnames != ['resource', 'start', 'end']:
        raise ValueError('expected exactly resource,start,end columns in that order')
    groups = {}
    count = 0
    for number, row in enumerate(reader, 1):
        count = number
        if number > MAX_ROWS:
            raise ValueError('input exceeds row limit')
        if None in row or any(v is None for v in row.values()):
            raise ValueError('incomplete or extra CSV field')
        resource = row['resource']
        if not resource.strip() or resource != resource.strip():
            raise ValueError('resource must be nonblank without surrounding whitespace')
        start, end = timestamp(row['start']), timestamp(row['end'])
        if end <= start:
            raise ValueError('end must be after start')
        groups.setdefault(resource, []).append((start, end, number))
    # Half-open intervals: touching endpoints do not conflict. Output positions
    # rather than resource names or appointment contents. Positions are data rows.
    pairs = []
    for intervals in groups.values():
        active = []
        for start, end, number in sorted(intervals):
            active = [(e, n) for e, n in active if e > start]
            for _, other in active:
                pairs.append(sorted((other, number)))
            active.append((end, number))
    return {'rows': count, 'overlap_count': len(pairs), 'overlaps': sorted(pairs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file')
    args = parser.parse_args()
    try:
        result = check(args.csv_file)
    except (OSError, ValueError, UnicodeError, csv.Error, OverflowError):
        print(json.dumps({'error': 'invalid or unreadable input; check format and documented limits'}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 1 if result['overlap_count'] else 0


if __name__ == '__main__':
    sys.exit(main())
