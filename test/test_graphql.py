"""
Tests for Phase 4.1: GraphQL API endpoint.
"""

import asyncio

import pytest

# ============================================================================
# TestGraphQLSchema — schema structure
# ============================================================================


class TestGraphQLSchema:
    def test_schema_importable(self):
        from app.graphql.schema import schema

        assert schema is not None

    def test_schema_has_query_type(self):
        from app.graphql.schema import schema

        assert schema._schema.query_type is not None

    def test_schema_has_mutation_type(self):
        from app.graphql.schema import schema

        assert schema._schema.mutation_type is not None

    def test_query_type_has_expected_fields(self):
        from app.graphql.schema import schema

        field_names = set(schema._schema.query_type.fields.keys())
        assert "me" in field_names
        assert "content" in field_names
        assert "contents" in field_names
        assert "categories" in field_names
        assert "comments" in field_names

    def test_mutation_type_has_expected_fields(self):
        from app.graphql.schema import schema

        field_names = set(schema._schema.mutation_type.fields.keys())
        assert "createContent" in field_names
        assert "updateContent" in field_names


# ============================================================================
# TestGraphQLEndpoint — HTTP endpoint behaviour
# ============================================================================


class TestGraphQLEndpoint:
    def test_graphql_route_registered_in_app(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("/graphql" in p for p in paths), f"No /graphql route in: {paths}"

    def test_graphql_get_returns_graphiql(self):
        """GET /graphql should return the GraphiQL UI (200 HTML)."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/graphql", headers={"Accept": "text/html"})
        assert response.status_code == 200

    def test_graphql_post_introspection_query(self):
        """POST a basic introspection query — server must respond with 200."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/graphql",
            json={"query": "{ __schema { queryType { name } } }"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["__schema"]["queryType"]["name"] == "Query"

    def test_graphql_not_blocked_by_rbac(self):
        """Unauthenticated requests to /graphql should not be redirected to /login."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        response = client.post(
            "/graphql",
            json={"query": "{ __typename }"},
        )
        assert response.status_code != 307, "/graphql must not be redirected to /login"


# ============================================================================
# TestGraphQLQueries — resolver-level checks via schema execution
# ============================================================================


class TestGraphQLQueries:
    def test_me_query_returns_null_when_unauthenticated(self):
        """me resolver must return null when context.user is None."""
        from unittest.mock import AsyncMock

        from app.graphql.context import GraphQLContext
        from app.graphql.schema import schema

        ctx = GraphQLContext(user=None, db=AsyncMock())
        result = asyncio.run(schema.execute("{ me { id username } }", context_value=ctx))
        assert result.errors is None
        assert result.data["me"] is None

    def test_contents_query_field_exists_in_schema(self):
        from app.graphql.schema import schema

        field_names = set(schema._schema.query_type.fields.keys())
        assert "contents" in field_names

    def test_categories_query_field_exists_in_schema(self):
        from app.graphql.schema import schema

        field_names = set(schema._schema.query_type.fields.keys())
        assert "categories" in field_names

    def test_comments_query_accepts_content_id_argument(self):
        from app.graphql.schema import schema

        comments_field = schema._schema.query_type.fields["comments"]
        arg_names = set(comments_field.args.keys())
        assert "contentId" in arg_names

    def test_contents_query_accepts_limit_and_offset(self):
        from app.graphql.schema import schema

        contents_field = schema._schema.query_type.fields["contents"]
        arg_names = set(contents_field.args.keys())
        assert "limit" in arg_names
        assert "offset" in arg_names


# ============================================================================
# TestGraphQLMutations — mutation schema checks
# ============================================================================


class TestGraphQLMutations:
    def test_create_content_accepts_input(self):
        from app.graphql.schema import schema

        field = schema._schema.mutation_type.fields["createContent"]
        arg_names = set(field.args.keys())
        assert "input" in arg_names

    def test_update_content_accepts_id_and_input(self):
        from app.graphql.schema import schema

        field = schema._schema.mutation_type.fields["updateContent"]
        arg_names = set(field.args.keys())
        assert "id" in arg_names
        assert "input" in arg_names

    def test_create_content_raises_without_auth(self):
        """createContent must raise when context.user is None."""
        from unittest.mock import AsyncMock

        from app.graphql.context import GraphQLContext
        from app.graphql.schema import schema

        ctx = GraphQLContext(user=None, db=AsyncMock())
        result = asyncio.run(
            schema.execute(
                'mutation { createContent(input: {title: "T", body: "B"}) { id } }',
                context_value=ctx,
            )
        )
        assert result.errors is not None and len(result.errors) > 0


# ============================================================================
# TestGraphQLContext — context dataclass
# ============================================================================


class TestGraphQLContext:
    def test_context_has_user_and_db_fields(self):
        from unittest.mock import AsyncMock, MagicMock

        from app.graphql.context import GraphQLContext

        ctx = GraphQLContext(user=MagicMock(), db=AsyncMock())
        assert hasattr(ctx, "user")
        assert hasattr(ctx, "db")

    def test_context_user_can_be_none(self):
        from unittest.mock import AsyncMock

        from app.graphql.context import GraphQLContext

        ctx = GraphQLContext(user=None, db=AsyncMock())
        assert ctx.user is None
