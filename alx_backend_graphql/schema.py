import graphene
from crm.schema import Query as CRMQuery


class Query(CRMQuery, graphene.ObjectType):
    """
    Root Query for the GraphQL API.
    """
    pass


schema = graphene.Schema(query=Query)
