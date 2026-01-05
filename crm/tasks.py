from datetime import datetime
from decimal import Decimal, InvalidOperation

from celery import shared_task
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"
REPORT_LOG = "/tmp/crm_report_log.txt"


@shared_task
def generate_crm_report():
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    transport = RequestsHTTPTransport(url=GRAPHQL_ENDPOINT, verify=True, retries=2)
    client = Client(transport=transport, fetch_schema_from_transport=False)

    query = gql(
        """
        query CRMReport {
          allCustomers {
            edges { node { id } }
          }
          allOrders {
            edges {
              node {
                id
                totalAmount
              }
            }
          }
        }
        """
    )

    data = client.execute(query)

    customers_edges = (data.get("allCustomers") or {}).get("edges") or []
    orders_edges = (data.get("allOrders") or {}).get("edges") or []

    total_customers = len(customers_edges)
    total_orders = len(orders_edges)

    revenue = Decimal("0")
    for edge in orders_edges:
        node = edge.get("node") or {}
        val = node.get("totalAmount")
        if val is None:
            continue
        try:
            revenue += Decimal(str(val))
        except (InvalidOperation, TypeError, ValueError):
            # Ignore malformed values
            continue

    line = f"{ts} - Report: {total_customers} customers, {total_orders} orders, {revenue} revenue\n"
    with open(REPORT_LOG, "a", encoding="utf-8") as f:
        f.write(line)

    return line
