# SSBulkVids

Bulk-create Shotstack videos from CSV data and a reusable JSON template.

## Pipeline

1. Create a Shotstack edit JSON template and put `{{column_name}}` placeholders
   where CSV values should be inserted.
2. Add one video variant per row in a CSV (the header names must match the
   placeholders).
3. Set `SHOTSTACK_API_KEY` and submit the batch:

```bash
export SHOTSTACK_API_KEY="your-key"
python3 bulk_videos.py data.csv template.json --wait --manifest renders.csv
```

The script submits one render per row and writes render IDs, final video URLs,
statuses, and errors to the manifest. It uses only Python's standard library.
Use `--dry-run` to validate the CSV/template without making API requests:

```bash
python3 bulk_videos.py data.csv template.json --dry-run
```

The default API is production (`https://api.shotstack.io/v1`). Set
`SHOTSTACK_ENDPOINT` to use another Shotstack environment. Keep API keys in
environment variables; do not put them in CSV or template files.