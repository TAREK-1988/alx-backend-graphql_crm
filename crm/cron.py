from datetime import datetime

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport


GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"
HEARTBEAT_LOG = "/tmp/crm_heartbeat_log.txt"
LOW_STOCK_LOG = "/tmp/low_stock_updates_log.txt"


def log_crm_heartbeat():
    ts = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

    try:
        transport = RequestsHTTPTransport(
            url=GRAPHQL_ENDPOINT,
            verify=True,
            retries=1,
        )
        client = Client(
            transport=transport,
            fetch_schema_from_transport=False,
        )
        query = gql("{ hello }")
        client.execute(query)
    except Exception:
        pass

    with open(HEARTBEAT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} CRM is alive\n")


def update_low_stock():
    ts = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

    transport = RequestsHTTPTransport(
        url=GRAPHQL_ENDPOINT,
        verify=True,
        retries=1,
    )
    client = Client(
        transport=transport,
        fetch_schema_from_transport=False,
    )

    mutation = gql(
        """
        mutation {
          updateLowStockProducts {
            message
            updatedProducts {
              name
              stock
            }
          }
        }
        """
    )

    result = client.execute(mutation)
    data = result.get("updateLowStockProducts", {})
    products = data.get("updatedProducts", [])

    with open(LOW_STOCK_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} {data.get('message')}\n")
        for product in products:
            f.write(
                f"{ts} Product={product.get('name')} NewStock={product.get('stock')}\n"
            )
