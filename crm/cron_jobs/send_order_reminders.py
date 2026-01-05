#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"
LOG_FILE = "/tmp/order_reminders_log.txt"


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)

    transport = RequestsHTTPTransport(url=GRAPHQL_ENDPOINT, verify=True, retries=3)
    client = Client(transport=transport, fetch_schema_from_transport=False)

    query = gql(
        """
        query PendingOrders($orderDateGte: DateTime) {
          allOrders(orderDateGte: $orderDateGte) {
            edges {
              node {
                id
                customer {
                  email
                }
                orderDate
              }
            }
          }
        }
        """
    )

    data = client.execute(query, variable_values={"orderDateGte": since.isoformat()})

    ts = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    edges = (data.get("allOrders") or {}).get("edges") or []
    for edge in edges:
        node = edge.get("node") or {}
        order_id = node.get("id")
        email = (node.get("customer") or {}).get("email")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} OrderID={order_id} CustomerEmail={email}\n")

    print("Order reminders processed!")


if __name__ == "__main__":
    main()
