"""Automated RBAC Route Security Auditor.

Enumerates all FastAPI routes and cross-checks each against the authoritative
RBAC table in CLAUDE.md. Fails CI (exit code 1) if any route is unguarded
or guarded incorrectly.
"""

import sys
from typing import Any

from fastapi.routing import APIRoute, _IncludedRouter

from app.main import app

# Authoritative RBAC mapping according to CLAUDE.md specifications:
# Path prefix or exact path -> allowed role(s) or "public" / "authenticated"
EXPECTED_ROUTE_GUARDS: dict[str, dict[str, Any]] = {
    # Public endpoints
    "/health": {"type": "public"},
    "/auth/signup": {"type": "public"},
    "/auth/login": {"type": "public"},
    "/auth/refresh": {"type": "public"},
    # Authenticated (any valid user)
    "/auth/me": {"type": "authenticated"},
    # Role-gated endpoints
    "/internal": {"type": "role", "roles": {"planner"}},
    "/trainee": {"type": "role", "roles": {"trainee"}},
    "/institute": {"type": "role", "roles": {"institute_admin"}},
    "/panel": {"type": "role", "roles": {"panel_member"}},
    "/planner": {"type": "role", "roles": {"planner"}},
    "/employer": {"type": "role", "roles": {"employer"}},
}


def get_all_api_routes(application: Any) -> list[APIRoute]:
    """Recursively collect all APIRoutes from FastAPI app and included routers."""
    routes: list[APIRoute] = []
    for r in application.routes:
        if isinstance(r, _IncludedRouter):
            routes.extend(
                sub_r for sub_r in r.original_router.routes if isinstance(sub_r, APIRoute)
            )
        elif isinstance(r, APIRoute):
            routes.append(r)
    return routes


def extract_route_guards(route: APIRoute) -> dict[str, Any]:
    """Extract role requirements and auth dependencies from an APIRoute."""
    detected_roles: set[str] = set()
    is_authenticated = False
    has_own_scope = False

    def scan_dependant(dep: Any) -> None:
        nonlocal is_authenticated, has_own_scope
        call = getattr(dep, "call", None)
        if call is not None:
            call_name = getattr(call, "__name__", "")
            # Check closure variables if require_role factory was used
            if call_name == "_check_role":
                closure = getattr(call, "__closure__", None)
                if closure:
                    for cell in closure:
                        val = cell.cell_contents
                        if isinstance(val, (tuple, list, set)):
                            detected_roles.update(str(x) for x in val)
                        elif isinstance(val, str) and val in {
                            "trainee",
                            "institute_admin",
                            "employer",
                            "planner",
                            "panel_member",
                        }:
                            detected_roles.add(val)
                is_authenticated = True

            if call_name == "_check_scope":
                has_own_scope = True
                is_authenticated = True

            if call_name in ("get_current_user", "get_db_with_rls"):
                is_authenticated = True

        for sub_dep in getattr(dep, "dependencies", []):
            scan_dependant(sub_dep)

    scan_dependant(route.dependant)
    return {
        "roles": detected_roles,
        "is_authenticated": is_authenticated,
        "has_own_scope": has_own_scope,
    }


def find_expected_guard(path: str) -> dict[str, Any] | None:
    """Match route path against expected guard definitions."""
    # Check exact match first
    if path in EXPECTED_ROUTE_GUARDS:
        return EXPECTED_ROUTE_GUARDS[path]
    # Check prefix match
    for prefix, guard in EXPECTED_ROUTE_GUARDS.items():
        if path.startswith(prefix + "/") or path == prefix:
            return guard
    return None


def run_audit() -> int:
    """Run full RBAC audit and return exit code (0 = pass, 1 = fail)."""
    api_routes = get_all_api_routes(app)
    # Deduplicate by path + methods
    unique_routes: dict[tuple[str, str], APIRoute] = {}
    for r in api_routes:
        methods = ",".join(sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS")))
        if methods:
            unique_routes[(r.path, methods)] = r

    failures: list[str] = []
    audited_count = 0

    print("=" * 80)
    print("VIKAS Automated RBAC Route Security Audit")
    print("=" * 80)
    print(f"{'Method':<7} | {'Path':<45} | {'Expected':<18} | {'Status'}")
    print("-" * 80)

    for (path, methods), route in sorted(unique_routes.items(), key=lambda x: x[0][0]):
        # Skip OpenAPI internal schemas
        if path in ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"):
            continue

        audited_count += 1
        expected = find_expected_guard(path)
        actual = extract_route_guards(route)

        if expected is None:
            status = "FAIL (No RBAC specification for route)"
            failures.append(f"{methods} {path}: Undocumented route with no RBAC rule")
            expected_desc = "UNKNOWN"
        elif expected["type"] == "public":
            status = "PASS (Public)"
            expected_desc = "Public"
        elif expected["type"] == "authenticated":
            if actual["is_authenticated"]:
                status = "PASS (Authenticated)"
            else:
                status = "FAIL (Missing auth guard)"
                failures.append(f"{methods} {path}: Route must require authenticated user")
            expected_desc = "Authenticated"
        elif expected["type"] == "role":
            expected_roles = expected["roles"]
            if expected_roles.issubset(actual["roles"]) or expected_roles == actual["roles"]:
                status = f"PASS ({', '.join(sorted(actual['roles']))})"
            else:
                status = f"FAIL (Expected {', '.join(sorted(expected_roles))}, got {', '.join(sorted(actual['roles'])) or 'NONE'})"
                failures.append(
                    f"{methods} {path}: Expected role guard {expected_roles}, found {actual['roles']}"
                )
            expected_desc = f"Role: {', '.join(sorted(expected_roles))}"

        print(f"{methods:<7} | {path:<45} | {expected_desc:<18} | {status}")

    print("-" * 80)
    print(f"Total Routes Audited: {audited_count}")

    if failures:
        print(f"\n[ERROR] RBAC Audit Failed with {len(failures)} violations:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\n[SUCCESS] All routes verified! Zero unguarded or mismatched routes.")
    return 0


if __name__ == "__main__":
    sys.exit(run_audit())

