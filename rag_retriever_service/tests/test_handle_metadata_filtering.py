# tests/check_handle_metadata_filtering.py
import sys
import os

# Insert the absolute path to the src directory into sys.path.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

import pytest
from rag_retriever_service.src.filters.metadata_filter import create_filter_for_user_group
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator


def test_empty_user_groups():
    """
    If user_groups is empty, the function should return None.
    """
    result = create_filter_for_user_group([], "allow", "deny")
    assert result is None, "Expected None when user_groups is empty."


def test_single_user_group_structure():
    """
    Test that for a single user group, the returned filter has the expected structure.
    """
    user_groups = ["admin"]
    result = create_filter_for_user_group(user_groups, "allow", "deny")
    assert result is not None, "Expected a filter when user_groups is non-empty."
    assert isinstance(result, MetadataFilters)
    # Final filter should combine a public filter and an allowed-filter branch.
    assert hasattr(result, "filters")
    assert len(result.filters) == 2

    # Verify public filter.
    public_filter = result.filters[0]
    assert isinstance(public_filter, MetadataFilter)
    assert public_filter.key == "allow"
    assert public_filter.value == ""
    assert public_filter.operator == FilterOperator.EQ

    # Verify allowed filter.
    allowed_filter = result.filters[1]
    assert isinstance(allowed_filter, MetadataFilters)
    # For one user group, we expect one branch.
    assert len(allowed_filter.filters) == 1

    # Verify the branch structure.
    branch = allowed_filter.filters[0]
    assert isinstance(branch, MetadataFilters)
    # Each branch must have an allow clause and a deny clause.
    assert len(branch.filters) == 2


def test_multiple_user_groups_structure():
    """
    Test that for multiple user groups, the allowed filter contains a branch for each group.
    """
    user_groups = ["admin", "user"]
    result = create_filter_for_user_group(user_groups, "allow", "deny")
    assert result is not None
    # Final filter has two parts: public filter and allowed filter.
    assert isinstance(result, MetadataFilters)
    assert len(result.filters) == 2

    allowed_filter = result.filters[1]
    # There should be two branches for two user groups.
    assert isinstance(allowed_filter, MetadataFilters)
    assert len(allowed_filter.filters) == 2


def test_deny_clause_in_branch():
    """
    Verify that the deny clause in each branch contains both an empty check and a group check.
    """
    user_groups = ["group1"]
    result = create_filter_for_user_group(user_groups, "allow", "deny")
    allowed_filter = result.filters[1]
    branch = allowed_filter.filters[0]
    # Branch should have two clauses: allow_clause and deny_clause.
    allow_clause, deny_clause = branch.filters
    # allow_clause is a MetadataFilters with 2 filters.
    assert isinstance(allow_clause, MetadataFilters)
    assert len(allow_clause.filters) == 2
    # Check that one filter is an equality match for the group.
    found_allow_eq = any(
        f.operator == FilterOperator.EQ and f.value == "group1" for f in allow_clause.filters
    )
    found_allow_in = any(
        f.operator == FilterOperator.IN and f.value == ["group1"] for f in allow_clause.filters
    )
    assert found_allow_eq and found_allow_in, "Allow clause should match the group with EQ and IN."

    # deny_clause should also be a MetadataFilters with 2 filters.
    assert isinstance(deny_clause, MetadataFilters)
    assert len(deny_clause.filters) == 2
    # Check that one of the filters is checking for an empty deny value.
    found_deny_empty = any(
        isinstance(f, MetadataFilter) and f.value == "" for f in deny_clause.filters
    )
    assert found_deny_empty, "Deny clause should include an empty value check."