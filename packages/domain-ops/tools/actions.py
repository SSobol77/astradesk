# SPDX-License-Identifier: Apache-2.0
# packages/domain-ops/tools/actions.py

"""Narzędzia do wykonywania akcji operacyjnych w klastrze Kubernetes.

Moduł ten dostarcza funkcje, które mogą być wywoływane przez agentów SRE/DevOps
do zarządzania aplikacjami w środowisku Kubernetes. Każda akcja jest chroniona
przez mechanizmy RBAC i walidację, aby zapewnić bezpieczeństwo.
"""
from __future__ import annotations

import datetime
import logging
import os
from typing import Final

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.exceptions import ApiException

# ZMIANA: Import z `services/api-gateway`
from services.api_gateway.src.runtime.policy import AuthorizationError, require_role

logger = logging.getLogger(__name__)

# --- Konfiguracja ---

# Przestrzeń nazw Kubernetes, w której działają usługi.
KUBERNETES_NAMESPACE: Final[str] = os.getenv("KUBERNETES_NAMESPACE", "default")

# Biała lista nazw wdrożeń (Deployments), które można restartować.
ALLOWED_SERVICES: Final[set[str]] = {"webapp", "payments-api", "search-service"}

# Rola wymagana w claims JWT, aby móc wywołać tę funkcję.
REQUIRED_ROLE_RESTART: Final[str] = "sre"

# --- Inicjalizacja klienta Kubernetes ---

# Ten blok próbuje załadować konfigurację z wewnątrz klastra.
# Jeśli się nie uda (np. podczas lokalnego developmentu), loguje ostrzeżenie.
try:
    config.load_incluster_config()
    logger.info("Pomyślnie załadowano konfigurację Kubernetes z wewnątrz klastra.")
except config.ConfigException:
    logger.warning(
        "Nie udało się załadować konfiguracji 'in-cluster'. "
        "Funkcja restart_service będzie działać tylko wewnątrz klastra Kubernetes."
    )


async def restart_service(service: str, *, claims: dict | None = None) -> str:
    """Restartuje wdrożenie (Deployment) w Kubernetes poprzez mechanizm 'rollout restart'.

    Funkcja wykonuje następujące kroki:
    1. Weryfikuje, czy użytkownik ma wymaganą rolę ('sre').
    2. Sprawdza, czy usługa znajduje się na białej liście dozwolonych usług.
    3. Łączy się z API Kubernetes i wysyła żądanie 'patch', które aktualizuje
       adnotację wdrożenia, co wyzwala kontrolowany restart podów.

    Args:
        service: Nazwa wdrożenia (Deployment) do zrestartowania.
        claims: Claims z tokena JWT, używane do weryfikacji RBAC.

    Returns:
        Komunikat o statusie operacji.

    Raises:
        AuthorizationError: Jeśli użytkownik nie ma wymaganych uprawnień.
    """
    logger.info(f"Otrzymano żądanie restartu dla usługi: '{service}'")

    # Krok 1: Weryfikacja uprawnień użytkownika (RBAC)
    try:
        require_role(claims, REQUIRED_ROLE_RESTART)
    except AuthorizationError:
        logger.warning(f"Odmowa dostępu dla restartu usługi '{service}': brak wymaganej roli '{REQUIRED_ROLE_RESTART}'.")
        raise

    # Krok 2: Walidacja względem białej listy usług
    if service not in ALLOWED_SERVICES:
        logger.warning(f"Odmowa restartu: usługa '{service}' nie znajduje się na białej liście.")
        return f"Błąd: Usługa '{service}' nie jest autoryzowana do restartu."

    # Krok 3: Wykonanie akcji w Kubernetes
    try:
        patch_body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow().isoformat() + "Z"
                        }
                    }
                }
            }
        }

        async with client.ApiClient() as api_client:
            api = client.AppsV1Api(api_client)
            await api.patch_namespaced_deployment(
                name=service, namespace=KUBERNETES_NAMESPACE, body=patch_body
            )

        logger.info(f"Pomyślnie zlecono restart wdrożenia '{service}' w przestrzeni nazw '{KUBERNETES_NAMESPACE}'.")
        return f"Pomyślnie zlecono restart usługi '{service}'."

    except ApiException as e:
        if e.status == 404:
            logger.error(f"Nie udało się zrestartować usługi: wdrożenie '{service}' nie zostało znalezione w przestrzeni nazw '{KUBERNETES_NAMESPACE}'.")
            return f"Błąd: Usługa '{service}' nie została znaleziona."
        elif e.status == 403:
            logger.critical(
                f"KRYTYCZNY BŁĄD UPRAWNIEŃ: Service Account aplikacji nie ma uprawnień do "
                f"patchowania wdrożeń w przestrzeni nazw '{KUBERNETES_NAMESPACE}'. Treść błędu: {e.body}"
            )
            return "Błąd: Wystąpił wewnętrzny problem z uprawnieniami. Skontaktuj się z administratorem."
        else:
            logger.error(f"Nieoczekiwany błąd API Kubernetes podczas restartu usługi '{service}': {e.body}", exc_info=True)
            return f"Błąd: Wystąpił nieoczekiwany błąd API Kubernetes (status: {e.status})."
    except Exception as e:
        logger.critical(f"Nieoczekiwany błąd podczas próby restartu usługi '{service}': {e}", exc_info=True)
        return "Błąd: Wystąpił krytyczny błąd wewnętrzny."