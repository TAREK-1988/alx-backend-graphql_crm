#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANAGE_PY="$PROJECT_ROOT/manage.py"
LOG_FILE="/tmp/customer_cleanup_log.txt"

DELETED_COUNT=$(
  python3 "$MANAGE_PY" shell -c "
from datetime import timedelta
from django.utils import timezone
from crm.models import Customer
from django.db.models import Max

cutoff = timezone.now() - timedelta(days=365)

qs = Customer.objects.annotate(last_order=Max('orders__order_date')).filter(last_order__lt=cutoff) | \
     Customer.objects.annotate(last_order=Max('orders__order_date')).filter(last_order__isnull=True)

count = qs.distinct().count()
qs.distinct().delete()
print(count)
"
)

TS="$(date '+%d/%m/%Y-%H:%M:%S')"
echo "${TS} Deleted inactive customers: ${DELETED_COUNT}" >> "$LOG_FILE"
