# CRM Celery Report (Weekly)

This app includes a Celery + Celery Beat setup that generates a weekly CRM report using the GraphQL endpoint and logs it to:

- `/tmp/crm_report_log.txt`

## 1) Install Redis and dependencies

### Install Redis (example)
- Ensure Redis is running locally on:
  - `redis://localhost:6379/0`

### Install Python dependencies
```bash
pip install -r requirements.txt
