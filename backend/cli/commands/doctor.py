"""dci doctor — validate repo layout, required directories, and environment."""

import json
import os
import sys
import traceback


def _find_project_root() -> str:
    """Walk up from this file to find the directory containing pyproject.toml."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isfile(os.path.join(d, "pyproject.toml")):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


def _run_checks(root: str, verbose: bool = False) -> list[dict]:
    checks: list[dict] = []

    def check(name: str, passed: bool, message: str = "", detail: str = ""):
        entry = {"name": name, "passed": passed, "message": message}
        if verbose and detail:
            entry["detail"] = detail
        checks.append(entry)

    # 1. project_root
    pp = os.path.join(root, "pyproject.toml")
    check("project_root", os.path.isfile(pp), "pyproject.toml exists", f"path: {pp}")

    # 2. backend_package
    bp = os.path.join(root, "backend", "__init__.py")
    check("backend_package", os.path.isfile(bp), "backend/__init__.py exists", f"path: {bp}")

    # 3. cli_package
    cp = os.path.join(root, "backend", "cli", "main.py")
    check("cli_package", os.path.isfile(cp), "backend/cli/main.py exists", f"path: {cp}")

    # 4-6. required directories
    for name, rel in [("models_dir", "backend/models"), ("services_dir", "backend/services"), ("tests_dir", "backend/tests")]:
        dp = os.path.join(root, rel)
        check(name, os.path.isdir(dp), f"{rel}/ exists", f"path: {dp}")

    # 7. frontend_dir
    fp = os.path.join(root, "frontend")
    check("frontend_dir", os.path.isdir(fp), "frontend/ exists", f"path: {fp}")

    # 8. venv
    vp = os.path.join(root, ".venv", "bin", "python")
    check("venv", os.path.isfile(vp), ".venv/bin/python exists", f"path: {vp}")

    # 9. database_importable
    try:
        from backend.database import Base  # noqa: F401
        check("database_importable", True, "backend.database.Base importable")
    except Exception as exc:
        tb = traceback.format_exc() if verbose else ""
        check("database_importable", False, f"import failed: {exc}", tb)

    # 10. alembic_config
    ap = os.path.join(root, "alembic.ini")
    check("alembic_config", os.path.isfile(ap), "alembic.ini exists", f"path: {ap}")

    return checks


def cmd_doctor(args) -> None:
    root = _find_project_root()
    verbose = getattr(args, "verbose", False)
    json_output = getattr(args, "json_output", False)

    checks = _run_checks(root, verbose=verbose)
    all_ok = all(c["passed"] for c in checks)

    if json_output:
        print(json.dumps({"ok": all_ok, "checks": checks}))
    else:
        for c in checks:
            status = "PASS" if c["passed"] else "FAIL"
            line = f"  {status}  {c['name']}"
            if not c["passed"] and c.get("message"):
                line += f" -- {c['message']}"
            print(line)
            if verbose and c.get("detail"):
                for dl in c["detail"].splitlines():
                    print(f"         {dl}")
        passed = sum(1 for c in checks if c["passed"])
        total = len(checks)
        print(f"\n{passed}/{total} checks passed.")

    sys.exit(0 if all_ok else 1)
