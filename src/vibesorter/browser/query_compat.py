from __future__ import annotations


def install(server) -> None:
    original = server._query_rows

    def query_rows(db_path, params_or_vibe, query=None, *, limit, offset):
        if isinstance(params_or_vibe, dict):
            params = dict(params_or_vibe)
            sort = (params.get("sort", ["path"])[0] or "path").casefold()
            if sort not in {"path", "modified", "size", "confidence"}:
                params["sort"] = ["path"]
            return original(db_path, params, query, limit=limit, offset=offset)
        return original(db_path, params_or_vibe, query, limit=limit, offset=offset)

    server._query_rows = query_rows
