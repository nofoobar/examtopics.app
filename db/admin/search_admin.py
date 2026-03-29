from sqladmin import ModelView

from db.models.search import Search


class SearchAdmin(ModelView, model=Search):
    name = "Search"
    name_plural = "Searches"
    icon = "fa-solid fa-magnifying-glass"

    column_list = [
        Search.id,
        Search.search_term,
        Search.results_count,
        Search.ip_address,
        Search.created_at,
    ]
    column_searchable_list = [Search.search_term]
    column_sortable_list   = [Search.id, Search.search_term, Search.results_count, Search.created_at]

    can_create = False   # searches are logged automatically, not created by hand
    can_edit   = False
    can_delete = True
    can_export = True
