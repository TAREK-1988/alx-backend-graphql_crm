import graphene
from crm.schema import Query as CRMQuery
from crm.schema import Mutation as CRMMutation


class Query(CRMQuery, graphene.ObjectType):
    """
    Root Query for the GraphQL API.

    This class composes all query fields exposed by the CRM app
    into a single entry point for the GraphQL schema.
    """
    pass


class Mutation(CRMMutation, graphene.ObjectType):
    """
    Root Mutation for the GraphQL API.

    This class composes all mutation fields exposed by the CRM app
    into a single mutation entry point.
    """
    pass


schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
)
