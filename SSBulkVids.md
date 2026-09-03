# SSBulkVids Project Notes

## Purpose

This project bulk-creates Shotstack videos from CSV rows and a reusable JSON template. Each CSV row becomes one render request.

## Files

- `bulk_videos.py`: Python CLI. Uses only the standard library.
- `data.csv`: One video variant per row. Column names must match template placeholders.
- `template.json`: Shotstack edit JSON with placeholders such as `{{title}}` and `{{video_url}}`.
- `.env`: Local API configuration. This file is ignored by Git and must be recreated in a new environment.
- `renders.csv`: Render IDs, statuses, video URLs, and errors. Generated output and ignored by Git.
- `README.md`: Basic usage documentation.

## Setup In A New Environment

1. Clone or copy the repository.
2. Ensure Python 3.9 or newer is installed.
3. Create `.env` in the repository root:

   ```text
   SHOTSTACK_API_KEY=your-real-shotstack-key
   ```

4. Do not commit `.env` or share the key. The API key that was previously used during setup was exposed and should be revoked.
5. Make sure every media URL in `data.csv` is publicly accessible to Shotstack. Local file paths will not work.

## Current Edit

The current template renders a video from `{{video_url}}` for 10 seconds and overlays `{{title}}` for the first 5 seconds. The current CSV title is `My new video`.

The current video URL is an S3 signed URL and is temporary. Replace it with a fresh signed URL or, preferably, a permanent public media URL before rendering after it expires.

## Commands

Validate without making API requests:

```bash
python3 bulk_videos.py data.csv template.json --dry-run
```

Submit all CSV rows and wait for completion:

```bash
python3 bulk_videos.py data.csv template.json --wait --manifest renders.csv
```

Submit without waiting:

```bash
python3 bulk_videos.py data.csv template.json --manifest renders.csv
```

## How The Script Works

1. Loads `.env` if present. Existing shell environment variables take priority.
2. Reads the CSV with UTF-8 support.
3. Replaces `{{column_name}}` placeholders in the template.
4. Validates the resulting JSON.
5. Sends one POST request to Shotstack per CSV row.
6. Optionally polls each render until it is done, failed, or times out.
7. Writes results to `renders.csv`.

## Troubleshooting

- `set SHOTSTACK_API_KEY or use --dry-run`: `.env` is missing, malformed, or the command is being run outside the repository root.
- `This URL is not accessible`: the media URL is private, invalid, expired, or not a direct media file URL.
- Exit code `1`: at least one render failed.
- Exit code `2`: command-line usage or configuration error.
- For a failed render, inspect the `error` column in `renders.csv`.

## Moving To Cron

Cron jobs should use absolute paths and run from the repository directory. Example:

```text
0 9 * * * cd /workspaces/SSBulkVids && /usr/bin/python3 bulk_videos.py data.csv template.json --wait --manifest renders.csv >> cron.log 2>&1
```

Cron will use the `.env` loader, but the media URLs still need to remain valid when the job runs.
