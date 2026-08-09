"""Backend SaaS per GestLab.

Package contenente il backend FastAPI che riusa il core applicativo
(``core.services``, ``core.repositories``) ed espone le API REST multi-tenant.
"""

__all__ = ["auth", "tenant_repo"]
