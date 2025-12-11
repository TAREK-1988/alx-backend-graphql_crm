import re
from decimal import Decimal, InvalidOperation

import graphene
from graphene_django import DjangoObjectType
from django.utils import timezone

from .models import Customer, Product, Order


PHONE_REGEX = re.compile(r"^(\+?\d[\d\-]{6,20})$")


class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int()


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()


class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        errors = []

        if Customer.objects.filter(email=input.email).exists():
            errors.append("Email already exists.")

        phone = input.phone or ""
        if phone and not PHONE_REGEX.match(phone):
            errors.append("Invalid phone number format.")

        if errors:
            return CreateCustomer(customer=None, message=None, errors=errors)

        customer = Customer.objects.create(
            name=input.name,
            email=input.email,
            phone=phone or None,
        )

        return CreateCustomer(
            customer=customer,
            message="Customer created successfully.",
            errors=[],
        )


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        created_customers = []
        errors = []

        for index, customer_input in enumerate(input):
            row_errors = []

            if Customer.objects.filter(email=customer_input.email).exists():
                row_errors.append("Email already exists.")

            phone = customer_input.phone or ""
            if phone and not PHONE_REGEX.match(phone):
                row_errors.append("Invalid phone number format.")

            if row_errors:
                errors.append(f"Row {index}: " + "; ".join(row_errors))
                continue

            customer = Customer.objects.create(
                name=customer_input.name,
                email=customer_input.email,
                phone=phone or None,
            )
            created_customers.append(customer)

        return BulkCreateCustomers(
            customers=created_customers,
            errors=errors,
        )


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        errors = []
        price_decimal = None

        try:
            price_decimal = Decimal(str(input.price))
            if price_decimal <= 0:
                errors.append("Price must be positive.")
        except (InvalidOperation, TypeError):
            errors.append("Invalid price value.")

        stock = input.stock if input.stock is not None else 0
        if stock < 0:
            errors.append("Stock cannot be negative.")

        if errors:
            return CreateProduct(product=None, errors=errors)

        product = Product.objects.create(
            name=input.name,
            price=price_decimal,
            stock=stock,
        )

        return CreateProduct(product=product, errors=[])


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        errors = []

        try:
            customer_id_int = int(input.customer_id)
            customer = Customer.objects.get(id=customer_id_int)
        except (ValueError, Customer.DoesNotExist):
            errors.append("Invalid customer ID.")
            return CreateOrder(order=None, errors=errors)

        if not input.product_ids:
            errors.append("At least one product must be selected.")
            return CreateOrder(order=None, errors=errors)

        product_ids_int = []
        for pid in input.product_ids:
            try:
                product_ids_int.append(int(pid))
            except ValueError:
                errors.append(f"Invalid product ID: {pid}")

        products = list(Product.objects.filter(id__in=product_ids_int))
        if len(products) != len(set(product_ids_int)):
            errors.append("One or more product IDs are invalid.")

        if errors:
            return CreateOrder(order=None, errors=errors)

        total_amount = sum((p.price for p in products), Decimal("0.00"))
        order_date = input.order_date or timezone.now()

        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            order_date=order_date,
        )
        order.products.set(products)

        return CreateOrder(order=order, errors=[])


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


class Query(graphene.ObjectType):
    all_customers = graphene.List(CustomerType)

    def resolve_all_customers(self, info):
        return Customer.objects.all()
