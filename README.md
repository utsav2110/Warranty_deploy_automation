# Warranty Deploy Automation

Scheduled background jobs for the [Warranty Management System](https://github.com/utsav2110/Warranty-Management-System), run daily via GitHub Actions. They keep the Supabase (PostgreSQL) database clean and notify users before their warranties expire.

## What it does

| Job | Schedule (cron, UTC) | Local time (IST) | Script |
|---|---|---|---|
| **Delete Expired Items** | `31 18 * * *` | 12:01 AM | `daily/delete_expired.py` |
| **Daily Email Sender** | `30 11 * * *` | 5:00 PM | `daily/send_email.py` |

Both jobs can also be triggered manually from the **Actions** tab (`workflow_dispatch`).

### `daily/delete_expired.py`
Connects to Supabase and deletes every row in `warranty_items` whose `warranty_end_date` is in the past.

### `daily/send_email.py`
For every user with role `user`:
1. Finds warranty items expiring **tomorrow**.
2. If any exist, generates a PDF report of those items (including attached warranty images, when present).
3. Sends an HTML "Warranty Expiration Alert" email with an item summary and the PDF attached, via Gmail SMTP.

## Project structure

```
Warranty_deploy_automation/
├── .github/workflows/
│   ├── delete_expired.yml   # runs delete_expired.py daily
│   └── send_email.yml       # runs send_email.py daily
└── daily/
    ├── delete_expired.py
    └── send_email.py
```

## Configuration

Both workflows read credentials from GitHub Actions **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Used by | Description |
|---|---|---|
| `SUPABASE_HOST` | both | Supabase Postgres host |
| `SUPABASE_DB` | both | Database name |
| `SUPABASE_USER` | both | Database user |
| `SUPABASE_PASS` | both | Database password |
| `SENDER_MAIL` | send_email | Gmail address used to send notifications |
| `SENDER_PASS` | send_email | Gmail app password (not your regular password) |

The database is expected to already contain the `users` and `warranty_items` tables used by the main Warranty Management System app.

## Notes

- Email is sent over `smtp.gmail.com:465` (SSL) — the sender account must have an [app password](https://support.google.com/accounts/answer/185833) generated, since regular Gmail passwords won't work with SMTP.
- Deletion runs before the email job each day, so only warranties still on record are eligible for the expiration alert.
