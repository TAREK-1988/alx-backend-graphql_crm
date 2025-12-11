import re
from decimal import Decimal, InvalidOperation

import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.utils import timezone

from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter


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
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=True)

    customer = graphene.Field(CustomerType)

    def mutate(self, info, name, email, phone):
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists.")

        if phone and not PHONE_REGEX.match(phone):
            raise Exception("Invalid phone number format.")

        customer = Customer(
            name=name,
            email=email,
            phone=phone,
        )
        customer.save()

        return CreateCustomer(customer=customer)


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, customers):
        created_customers = []
        errors = []

        for index, customer_input in enumerate(customers):
            row_errors = []

            if Customer.objects.filter(email=customer_input.email).exists():
                row_errors.append("Email already exists.")

            phone = customer_input.phone or ""
            if phone and not PHONE_REGEX.match(phone):
                row_errors.append("Invalid phone number format.")

            if row_errors:
                errors.append(f"Row {index}: " + "; ".join(row_errors))
                continue

            customer = Customer(
                name=customer_input.name,
                email=customer_input.email,
                phone=phone or None,
            )
            customer.save()
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

    def mutate(self, info, input):
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

        product = Product(
            name=input.name,
            price=price_decimal,
            stock=stock,
        )
        product.save()

        return CreateProduct(product=product, errors=[])


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, input):
        errors = []

        try:
            customer_id_int = int(input.customer_id)
            customer = Customer.objects.get(id=customer_id_int)
        except (ValueError, Customer.DoesNotExist):
            errors.append("Invalid customer ID.")
            return CreateOrder(order=None, errors=errors)

        if not input.product_ids:
            errors.append("At least one product must be provided.")
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

        order = Order(
            customer=customer,
            total_amount=total_amount,
            order_date=order_date,
        )
        order.save()
        order.products.set(products)

        return CreateOrder(order=order, errors=[])


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


class Query(graphene.ObjectType):
    all_customers = graphene.List(CustomerType)
    all_customers = DjangoFilterConnectionField(CustomerNode)
    all_products = DjangoFilterConnectionField(ProductNode)
    all_orders = DjangoFilterConnectionField(OrderNode)

    def resolve_all_customers(self, info, **kwargs):
        return Customer.objects.all()
