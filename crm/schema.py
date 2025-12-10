import re
from decimal import Decimal, InvalidOperation

import graphene
from django.utils import timezone
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from .filters import CustomerFilter, ProductFilter, OrderFilter
from .models import Customer, Product, Order

PHONE_REGEX = re.compile(r"^(\+?\d[\d\-]{6,20})$")


# =========================
# GraphQL Types (Relay Nodes)
# =========================


class CustomerNode(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        filterset_class = CustomerFilter


class ProductNode(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        filterset_class = ProductFilter


class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        filterset_class = OrderFilter


# =========================
# Input Types for Mutations
# =========================


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


# =========================
# Input Types for Filters
# (used in Query arguments)
# =========================


class CustomerFilterInput(graphene.InputObjectType):
    name_icontains = graphene.String()
    email_icontains = graphene.String()
    created_at_gte = graphene.Date()
    created_at_lte = graphene.Date()
    phone_startswith = graphene.String()


class ProductFilterInput(graphene.InputObjectType):
    name_icontains = graphene.String()
    price_gte = graphene.Float()
    price_lte = graphene.Float()
    stock_gte = graphene.Int()
    stock_lte = graphene.Int()


class OrderFilterInput(graphene.InputObjectType):
    total_amount_gte = graphene.Float()
    total_amount_lte = graphene.Float()
    order_date_gte = graphene.Date()
    order_date_lte = graphene.Date()
    customer_name = graphene.String()
    product_name = graphene.String()
    product_id = graphene.ID()


# =========================
# Mutations
# =========================


class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerNode)
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        errors: list[str] = []

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

    customers = graphene.List(CustomerNode)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        created_customers: list[Customer] = []
        errors: list[str] = []

        for index, customer_input in enumerate(input):
            row_errors: list[str] = []

            if Customer.objects.filter(email=customer_input.email).exists():
                row_errors.append("Email already exists.")

            phone = customer_input.phone or ""
            if phone and not PHONE_REGEX.match(phone):
                row_errors.append("Invalid phone number format.")

            if row_errors:
                errors.append(
                    f"Row {index}: " + "; ".join(row_errors)
                )
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

    product = graphene.Field(ProductNode)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        errors: list[str] = []

        price_decimal: Decimal | None = None
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

    order = graphene.Field(OrderNode)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        errors: list[str] = []

        try:
            customer_id_int = int(input.customer_id)
            customer = Customer.objects.get(id=customer_id_int)
        except (ValueError, Customer.DoesNotExist):
            errors.append("Invalid customer ID.")
            return CreateOrder(order=None, errors=errors)

        if not input.product_ids:
            errors.append("At least one product must be provided.")
            return CreateOrder(order=None, errors=errors)

        product_ids_int: list[int] = []
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


# =========================
# Root Mutation
# =========================


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


# =========================
# Queries
# =========================


class Query(graphene.ObjectType):
    hello = graphene.String(description="Simple greeting message.")

    customer = relay.Node.Field(CustomerNode)
    product = relay.Node.Field(ProductNode)
    order = relay.Node.Field(OrderNode)

    all_customers = DjangoFilterConnectionField(
        CustomerNode,
        filter=CustomerFilterInput(),
        order_by=graphene.List(graphene.String),
    )
    all_products = DjangoFilterConnectionField(
        ProductNode,
        filter=ProductFilterInput(),
        order_by=graphene.List(graphene.String),
    )
    all_orders = DjangoFilterConnectionField(
        OrderNode,
        filter=OrderFilterInput(),
        order_by=graphene.List(graphene.String),
    )

    def resolve_hello(self, info, **kwargs) -> str:
        return "Hello, GraphQL!"

    def resolve_all_customers(self, info, filter=None, order_by=None, **kwargs):
        queryset = Customer.objects.all()
        filter_data = {}

        if filter:
            if filter.get("name_icontains"):
                filter_data["name_icontains"] = filter["name_icontains"]
            if filter.get("email_icontains"):
                filter_data["email_icontains"] = filter["email_icontains"]
            if filter.get("created_at_gte"):
                filter_data["created_at_gte"] = filter["created_at_gte"]
            if filter.get("created_at_lte"):
                filter_data["created_at_lte"] = filter["created_at_lte"]
            if filter.get("phone_startswith"):
                filter_data["phone_startswith"] = filter["phone_startswith"]

        queryset = CustomerFilter(data=filter_data, queryset=queryset).qs

        if order_by:
            queryset = queryset.order_by(*order_by)

        return queryset

    def resolve_all_products(self, info, filter=None, order_by=None, **kwargs):
        queryset = Product.objects.all()
        filter_data = {}

        if filter:
            if filter.get("name_icontains"):
                filter_data["name_icontains"] = filter["name_icontains"]
            if filter.get("price_gte") is not None:
                filter_data["price_gte"] = filter["price_gte"]
            if filter.get("price_lte") is not None:
                filter_data["price_lte"] = filter["price_lte"]
            if filter.get("stock_gte") is not None:
                filter_data["stock_gte"] = filter["stock_gte"]
            if filter.get("stock_lte") is not None:
                filter_data["stock_lte"] = filter["stock_lte"]

        queryset = ProductFilter(data=filter_data, queryset=queryset).qs

        if order_by:
            queryset = queryset.order_by(*order_by)

        return queryset

    def resolve_all_orders(self, info, filter=None, order_by=None, **kwargs):
        queryset = Order.objects.all()
        filter_data = {}

        if filter:
            if filter.get("total_amount_gte") is not None:
                filter_data["total_amount_gte"] = filter["total_amount_gte"]
            if filter.get("total_amount_lte") is not None:
                filter_data["total_amount_lte"] = filter["total_amount_lte"]
            if filter.get("order_date_gte"):
                filter_data["order_date_gte"] = filter["order_date_gte"]
            if filter.get("order_date_lte"):
                filter_data["order_date_lte"] = filter["order_date_lte"]
            if filter.get("customer_name"):
                filter_data["customer_name"] = filter["customer_name"]
            if filter.get("product_name"):
                filter_data["product_name"] = filter["product_name"]
            if filter.get("product_id"):
                filter_data["product_id"] = filter["product_id"]

        queryset = OrderFilter(data=filter_data, queryset=queryset).qs

        if order_by:
            queryset = queryset.order_by(*order_by)

        return queryset
