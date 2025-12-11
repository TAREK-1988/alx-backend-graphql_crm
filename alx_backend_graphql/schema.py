import graphene


class Query(graphene.ObjectType):
    hello = graphene.String(description="Simple hello field.")

    def resolve_hello(self, info) -> str:
        return "Hello, GraphQL!"


schema = graphene.Schema(query=Query)
