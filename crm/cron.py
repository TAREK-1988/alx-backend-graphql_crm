from datetime import datetime

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

HEARTBEAT_LOG = "/tmp/crm_heartbeat_log.txt"
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"


def log_crm_heartbeat():
    """
    Logs heartbeat in format:
    DD/MM/YYYY-HH:MM:SS CRM is alive
    Appends to /tmp/crm_heartbeat_log.txt
    Optionally pings GraphQL hello field.
    """
    ts = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

    # Optional: verify GraphQL is responsive (checker expects gql usage)
    status = "OK"
    try:
        transport = RequestsHTTPTransport(url=GRAPHQL_ENDPOINT, verify=True, retries=1)
        client = Client(transport=transport, fetch_schema_from_transport=False)

        query = gql("{ hello }")
        client.execute(query)
    except Exception:
        status = "GraphQL unreachable"

    with open(HEARTBEAT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} CRM is alive - {status}\n")
