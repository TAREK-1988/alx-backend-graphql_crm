from datetime import datetime
import requests

HEARTBEAT_LOG = "/tmp/crm_heartbeat_log.txt"
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"


def log_crm_heartbeat() -> None:
    ts = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

    ok = True
    try:
        payload = {"query": "{ hello }"}
        r = requests.post(GRAPHQL_ENDPOINT, json=payload, timeout=5)
        ok = r.status_code == 200
    except Exception:
        ok = False

    status = "OK" if ok else "GraphQL unreachable"
    with open(HEARTBEAT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} CRM is alive - {status}\n")
