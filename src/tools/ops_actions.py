# src/tools/ops_actions.py
"""
Akcje operacyjne wykonywane przez agenta SRE/DevOps (restart serwisu itp.)
z *twardym* RBAC opartym o role w claims (OIDC/JWT).

Zasada:
- metoda przyjmuje 'claims' (dict) i sprawdza wymagane role.
- przy braku roli rzuca PermissionError (łapany wyżej i zamieniany na komunikat).

Dodatkowo:
- lista dozwolonych usług (allow-list),
- przy powodzeniu warto dodać wpis audytu (wywoływane przez warstwę wyżej).
"""
from __future__ import annotations
from typing import Final

from runtime.policy import require_role

ALLOWED_SERVICES: Final[set[str]] = {"webapp", "payments", "search"}
REQUIRED_ROLE_RESTART: Final[str] = "sre"   # rola wymagana do restartu

async def restart_service(service: str, *, claims: dict | None = None) -> str:
    """
    Restartuje usługę 'service' (symulacja) — tylko dla ról z uprawnieniem 'sre'.
    :param service: nazwa usługi
    :param claims: claims z JWT (zawiera role)
    :return: komunikat o wyniku operacji
    :raise PermissionError: jeżeli brak roli 'sre'
    """
    # RBAC
    require_role(claims, REQUIRED_ROLE_RESTART)

    # Polityka: pozwalamy tylko na wybrane usługi
    if service not in ALLOWED_SERVICES:
        return f"Odmowa: serwis '{service}' nie jest dozwolony polityką."

    # W prawdziwym systemie wywołaj Ansible/Argo/K8s API z RBAC + audyt
    return f"Zlecono restart usługi '{service}'. Status: OK (symulacja)."
