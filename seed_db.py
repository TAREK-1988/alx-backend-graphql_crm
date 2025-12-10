import os
from decimal import Decimal

import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "graphql_crm.settings")
django.setup()

from crm.models import Customer, Product, Order  # noqa: E402


def run():
    # Optional: clear existing data
    Order.objects.all().delete()
    Product.objects.all().delete()
    Customer.objects.all().delete()

    # Create customers
    alice = Customer.objects.create(
        name="Alice Johnson",
        email="alice@example.com",
        phone="+1234567890",
    )
    bob = Customer.objects.create(
        name="Bob Smith",
        email="bob@example.com",
        phone="123-456-7890",
    )
    carol = Customer.objects.create(
        name="Carol Davis",
        email="carol@example.com",
        phone=None,
    )

    # Create products
    laptop = Product.objects.create(
        name="Laptop",
        price=Decimal("999.99"),
        stock=10,
    )
    mouse = Product.objects.create(
        name="Wireless Mouse",
        price=Decimal("25.50"),
        stock=100,
    )
    keyboard = Product.objects.create(
        name="Mechanical Keyboard",
        price=Decimal("79.90"),
        stock=50,
    )

    # Create orders
    order1_total = laptop.price + mouse.price
    order1 = Order.objects.create(
        customer=alice,
        total_amount=order1_total,
        order_date=timezone.now(),
    )
    order1.products.set([laptop, mouse])

    order2_total = mouse.price + keyboard.price
    order2 = Order.objects.create(
        customer=bob,
        total_amount=order2_total,
        order_date=timezone.now(),
    )
    order2.products.set([mouse, keyboard])

    order3_total = keyboard.price
    order3 = Order.objects.create(
        customer=carol,
        total_amount=order3_total,
        order_date=timezone.now(),
    )
    order3.products.set([keyboard])

    print("Database seeded successfully.")


if __name__ == "__main__":
    run()
