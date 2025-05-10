from typing import List, Optional
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator

def create_filter_for_user_group(user_groups: List[str], allow_filter_key: str, deny_filter_key: str) -> Optional[MetadataFilters]:
    """
    Create a composite MetadataFilters object to filter vector database chunks based on user groups.

    Filtering Logic:
    ----------------
    A record is included if ANY of the following conditions holds:

      1. **Public Record:** The record's `allow_filter_key` is an empty string ("").
      
      2. **Allowed Record with Deny Exceptions:**
         For records with a nonempty allow field, the record is allowed if there exists a user group 
         in `user_groups` such that:
           - The record's allow field matches that group (using either an equality check or an 
             array-membership check), and
           - The record's deny field is either empty OR equals that same group.
    
    Args:
      user_groups (List[str]): List of user group identifiers.
      allow_filter_key (str): Metadata key used to indicate allowed groups.
      deny_filter_key (str): Metadata key used to indicate denied groups.

    Returns:
      Optional[MetadataFilters]: A composite filter object encoding the above logic,
      or None if no user groups are provided.
    """
    if not user_groups:
        return None
    
    public_filter = MetadataFilter(
        key=allow_filter_key,
        value="",
        operator=FilterOperator.EQ
    )

    group_filters = []
    for group in user_groups:
        allow_eq = MetadataFilter(
            key=allow_filter_key,
            value=group,
            operator=FilterOperator.EQ
        )
        allow_in = MetadataFilter(
            key=allow_filter_key,
            value=[group],
            operator=FilterOperator.IN
        )
        allow_clause = MetadataFilters(
            filters=[allow_eq, allow_in],
            logical_operator="OR"
        )

        deny_empty = MetadataFilter(
            key=deny_filter_key,
            value="",
            operator=FilterOperator.EQ
        )
        deny_eq = MetadataFilter(
            key=deny_filter_key,
            value=group,
            operator=FilterOperator.EQ
        )
        deny_in = MetadataFilter(
            key=deny_filter_key,
            value=[group],
            operator=FilterOperator.IN
        )
        deny_group = MetadataFilters(
            filters=[deny_eq, deny_in],
            logical_operator="OR"
        )
        deny_clause = MetadataFilters(
            filters=[deny_empty, deny_group],
            logical_operator="OR"
        )

        branch = MetadataFilters(
            filters=[allow_clause, deny_clause],
            logical_operator="AND"
        )
        group_filters.append(branch)

    if group_filters:
        allowed_filter = MetadataFilters(
            filters=group_filters,
            logical_operator="OR"
        )
        final_filter = MetadataFilters(
            filters=[public_filter, allowed_filter],
            logical_operator="OR"
        )
    else:
        final_filter = MetadataFilters(
            filters=[public_filter],
            logical_operator="OR"
        )

    return final_filter