# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/model_gateway/base.py
Project: AstraDesk Framework — API Gateway
Description:
    Core contracts, types, and helpers for the Model Gateway layer. Provides a
    stable, provider-agnostic interface for chat models (LLMs), a shared error
    taxonomy, message/parameter schemas, streaming primitives, and adapters for
    common wire formats (e.g., OpenAI-/Anthropic-style messages).

Author: Siergej Sobolewski
Since: 2025-10-07

Scope & responsibilities
------------------------
- Message & params:
  * `LLMMessage` — minimal chat unit (`role`, `content`) with helpers.
  * `ChatParams` — normalized generation params (clamped ranges, extras).
  * `Usage`, `ChatChunk` — accounting and streaming fragments.
- Provider contract:
  * `LLMProvider` Protocol — two methods: `chat()` (full response) and
    `stream()` (async iterator of `ChatChunk`).
- Error model (domain exceptions):
  * `ModelGatewayError` — base error with rich diagnostics (provider, status, ids).
  * `ProviderTimeout`, `ProviderOverloaded`, `ProviderServerError`,
    `TokenLimitExceeded` — focused subclasses with factories for httpx/SDK mapping.
- Utilities:
  * Adapters: `to_openai_messages()`, `to_anthropic_messages()`.
  * Validation: `validate_conversation()`.
  * Optional tokenization contract: `Tokenizer` + `NoopTokenizer`.

Design principles
-----------------
- Transport-agnostic core: providers implement only serialization/transport.
- Clear separation of concerns: orchestration/business logic lives outside.
- Observability-first: all errors carry context (request_id, retry_after, etc.).
- Async-native: streaming via `AsyncIterator[ChatChunk]`, no blocking I/O.
- Extensibility: add new providers by implementing `LLMProvider` and reusing
  base adapters/errors; keep provider modules thin and stateless.

Error mapping (best practice)
-----------------------------
- Map HTTP 429 → `ProviderOverloaded` (parse RateLimit headers when present).
- Map HTTP 5xx → `ProviderServerError` (with retryability heuristics).
- Map read/connect timeouts → `ProviderTimeout`.
- Map context/token issues → `TokenLimitExceeded` (with reduction advice).
- For everything else, raise `ModelGatewayError` with safe `details`.

Security & safety
-----------------
- Never log secrets or raw bodies in production; prefer structured, redacted logs.
- Enforce per-request budgets (max_tokens, wall-clock deadlines) at call sites.
- Keep import-time side effects to zero (no network/filesystem actions).

Performance & testing
---------------------
- Providers should reuse HTTP clients/sessions (connection pooling).
- Favor deterministic unit tests with fakes/mocks (no real network).
- Keep adapters minimal; push heavy transforms to orchestration if needed.

Usage (example)
---------------
>>> class MyProvider(LLMProvider):
...     async def chat(self, messages, *, params=None, tokenizer=None, request_id=None) -> str:
...         # serialize → call remote → map errors → return text
...         ...
...     async def stream(self, messages, *, params=None, tokenizer=None, request_id=None):
...         # yield ChatChunk(...) pieces
...         ...
>>> validate_conversation([LLMMessage.system("You are helpful."), LLMMessage.user("Hi!")])
>>> p = ChatParams(max_tokens=256, temperature=0.2).normalized()

Notes (PL)
----------
- Warstwa „Model Gateway” standaryzuje kontrakty i błędy, dzięki czemu
  providerzy (OpenAI/Bedrock/vLLM/…) są wymienni bez zmian w reszcie systemu.
- Streaming (`stream()`) jest obowiązkowy w implementacjach providerów.

"""  # noqa: D205

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from core.src.astradesk_core.exceptions import ProviderOverloadedError, ProviderServerError
from core.src.astradesk_core.exceptions import ProviderTimeoutError, TokenLimitExceededError


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Wyjątki specyficzne dla warstwy Model Gateway
# ---------------------------------------------------------------------------

# ===========================
# ModelGatewayError
# ===========================
@dataclass
class ModelGatewayError(RuntimeError):
    """Ogólny błąd warstwy Model Gateway, niosący pełny kontekst diagnostyczny.

    Pola (wszystkie opcjonalne poza 'message'):
        message      : zwięzły opis problemu (np. "Rate limited / overloaded"),
        provider     : identyfikator dostawcy ("openai", "bedrock", "vllm", ...),
        status_code  : kod statusu (np. HTTP 429/500 lub ekwiwalent SDK),
        request_id   : identyfikator żądania/trasowania (np. X-Request-Id),
        retry_after  : rekomendowany czas odczekania w sekundach,
        details      : zdekodowane szczegóły (dict/str) z odpowiedzi providera,
        raw          : surowy obiekt odpowiedzi/błędu (httpx.Response, boto3 obj, itd.).
    """

    message: str
    provider: str | None = None
    status_code: int | None = None
    request_id: str | None = None
    retry_after: float | None = None
    details: Any = None
    raw: Any = None

    def __str__(self) -> str:
        """Zwraca zwięzłą, czytelną reprezentację błędu.

        Format wyjściowy jest zoptymalizowany pod kątem logowania i szybkiej
        diagnostyki, zawierając kluczowe informacje kontekstowe, takie jak
        dostawca, status i ID żądania.

        Returns
        -------
            Sformatowany string reprezentujący błąd, np.:
            "Rate limited [provider=openai] [status=429] [request_id=...]"

        """
        # Składamy kontekst komunikat do logów/tracingu.
        parts = [self.message or self.__class__.__name__]
        if self.provider:
            parts.append(f"[provider={self.provider}]")
        if self.status_code is not None:
            parts.append(f"[status={self.status_code}]")
        if self.request_id:
            parts.append(f"[request_id={self.request_id}]")
        if self.retry_after is not None:
            parts.append(f"[retry_after={self.retry_after:.2f}s]")
        return " ".join(parts)

    # ---- Fabryki ułatwiające mapowanie błędów HTTP/SDK na wyjątki domenowe ----

    @classmethod
    def from_httpx(
        cls,
        exc: httpx.HTTPError,  # noqa: F821 # type: ignore
        *,
        provider: str,
        fallback_message: str = "Provider HTTP error",
        request_id_header: str = "x-request-id",
    ) -> ModelGatewayError:
        """Mapuje httpx.HTTPError/HTTPStatusError → ModelGatewayError z kontekstem.

        (Lokalny import httpx, by nie wymuszać zależności poza providerami.).
        """
        import httpx  # lazy import
        status = None
        req_id = None
        retry_after = None
        details: Any = None
        raw = getattr(exc, "response", None)

        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            try:
                req_id = exc.response.headers.get(request_id_header) or exc.response.headers.get("x-amzn-RequestId")
            except Exception:
                req_id = None
            try:
                ra = exc.response.headers.get("retry-after")
                if ra is not None:
                    retry_after = float(ra)
            except Exception:
                retry_after = None
            try:
                details = exc.response.json()
            except Exception:
                try:
                    details = exc.response.text
                except Exception:
                    details = None

        return cls(
            message=fallback_message,
            provider=provider,
            status_code=status,
            request_id=req_id,
            retry_after=retry_after,
            details=details,
            raw=raw,
        )

    @classmethod
    def from_response(
        cls,
        *,
        provider: str,
        message: str,
        status_code: int | None = None,
        request_id: str | None = None,
        retry_after: float | None = None,
        details: Any = None,
        raw: Any = None,
    ) -> ModelGatewayError:
        """Tworzy instancję ModelGatewayError z dowolnego typu odpowiedzi lub błędu.

        Ta uniwersalna metoda fabryczna jest przeznaczona do użycia w sytuacjach,
        gdy błąd nie pochodzi bezpośrednio z `httpx`, np. z odpowiedzi klienta
        SDK (jak `boto3` dla AWS Bedrock) lub z niestandardowej logiki.
        Umożliwia ujednolicenie obsługi błędów w całym systemie.

        Args:
        ----
            provider: Identyfikator dostawcy (np. "bedrock", "custom_sdk").
            message: Zwięzły, czytelny dla człowieka opis problemu.
            status_code: Opcjonalny kod statusu (np. z odpowiedzi HTTP).
            request_id: Opcjonalny identyfikator żądania do celów śledzenia.
            retry_after: Opcjonalna, rekomendowana liczba sekund do odczekania
                przed ponowną próbą.
            details: Opcjonalne, ustrukturyzowane szczegóły błędu (np.
                sparsowany JSON z ciała odpowiedzi).
            raw: Opcjonalny, surowy obiekt błędu lub odpowiedzi do celów
                diagnostycznych (np. instancja odpowiedzi `boto3`).

        Returns:
        -------
            Nowa instancja `ModelGatewayError` z wypełnionymi polami.

        Example:
        -------
            Użycie wewnątrz providera AWS Bedrock:

            .. code-block:: python

                try:
                    # ... wywołanie API Bedrock ...
                except botocore.exceptions.ClientError as e:
                    response_meta = e.response.get("ResponseMetadata", {})
                    raise ModelGatewayError.from_response(
                        provider="bedrock",
                        message="Bedrock service error",
                        status_code=response_meta.get("HTTPStatusCode"),
                        request_id=response_meta.get("RequestId"),
                        details=e.response.get("Error"),
                        raw=e.response,
                    )

        """
        return cls(
            message=message,
            provider=provider,
            status_code=status_code,
            request_id=request_id,
            retry_after=retry_after,
            details=details,
            raw=raw,
        )

# ===========================
# ProviderTimeoutError
# ===========================
@dataclass(slots=True)
class ProviderTimeoutError(ModelGatewayError):
    """Wyjątek rzucany, gdy zapytanie do dostawcy przekroczyło limit czasu."""

    timeout: float | None = None
    elapsed: float | None = None
    phase: str | None = None
    endpoint: str | None = None
    attempts: int | None = None

    def __str__(self) -> str:
        """Zwraca zwięzłą, bogatą w kontekst reprezentację błędu timeout.

        Format wyjściowy jest zoptymalizowany pod kątem logowania i szybkiej
        diagnostyki, zawierając kluczowe informacje takie jak faza
        połączenia, skonfigurowany limit czasu i rzeczywisty czas,
        jaki upłynął.

        Returns
        -------
            Sformatowany string reprezentujący błąd, np.:
            "Provider HTTP timeout [provider=openai] [phase=read] [timeout=30.0s]"

        """
        parts = [self.message or "Provider request timed out"]
        if self.provider:
            parts.append(f"[provider={self.provider}]")
        if self.endpoint:
            parts.append(f"[endpoint={self.endpoint}]")
        if self.phase:
            parts.append(f"[phase={self.phase}]")
        if self.timeout is not None:
            parts.append(f"[timeout={self.timeout}s]")
        if self.elapsed is not None:
            parts.append(f"[elapsed={self.elapsed:.3f}s]")
        if self.attempts is not None:
            parts.append(f"[attempts={self.attempts}]")
        if self.request_id:
            parts.append(f"[request_id={self.request_id}]")
        return " ".join(parts)

    # -------------------------
    # Fabryki / helpery mapujące
    # -------------------------

    @classmethod
    def from_httpx_timeout(
        cls,
        *,
        provider: str,
        timeout: float | None = None,
        endpoint: str | None = None,
        phase: str | None = None,
        attempts: int | None = None,
        elapsed: float | None = None,
        request_id: str | None = None,
        details: Any = None,
        raw: Any = None,
        message: str = "Provider HTTP timeout",
    ) -> "ProviderTimeoutError":  # noqa: UP037
        """Tworzy instancję błędu na podstawie wyjątku timeout z biblioteki `httpx`.

        Args:
        ----
            provider: Identyfikator dostawcy.
            timeout: Skonfigurowany limit czasu w sekundach.
            endpoint: Adres URL, do którego kierowane było zapytanie.
            phase: Faza połączenia, w której wystąpił timeout (np. "read", "connect").
            attempts: Liczba prób wykonania zapytania.
            elapsed: Rzeczywisty czas, jaki upłynął do wystąpienia błędu.
            request_id: Identyfikator żądania.
            details: Dodatkowe szczegóły błędu.
            raw: Surowy obiekt wyjątku `httpx`.
            message: Niestandardowy komunikat błędu.

        Returns:
        -------
            Nowa instancja `ProviderTimeoutError`.

        """
        return cls(
            message=message,
            provider=provider,
            status_code=None,
            request_id=request_id,
            retry_after=None,
            details=details,
            raw=raw,
            timeout=timeout,
            elapsed=elapsed,
            phase=phase,
            endpoint=endpoint,
            attempts=attempts,
        )

    @classmethod
    def from_asyncio_timeout(
        cls,
        *,
        provider: str,
        timeout: float | None,
        endpoint: str | None = None,
        attempts: int | None = None,
        elapsed: float | None = None,
        message: str = "Provider asyncio timeout",
        raw: Any = None,
    ) -> "ProviderTimeoutError":  # noqa: UP037
        """Utwórz wyjątek na bazie `asyncio.TimeoutError` (gdy stosujesz `asyncio.wait_for`)."""
        return cls(
            message=message,
            provider=provider,
            timeout=timeout,
            elapsed=elapsed,
            phase="overall",
            endpoint=endpoint,
            attempts=attempts,
            raw=raw,
        )


    @classmethod
    def from_deadline(
        cls,
        *,
        provider: str,
        deadline_seconds: float,
        started_at_seconds: float | None = None,
        endpoint: str | None = None,
        attempts: int | None = None,
        message: str = "Provider deadline exceeded",
    ) -> "ProviderTimeoutError":  # noqa: UP037
        """Tworzy instancję błędu na podstawie przekroczenia własnego limitu czasowego (deadline)."""
        elapsed = None
        if started_at_seconds is not None:
            elapsed = max(0.0, time.time() - started_at_seconds)

        return cls(
            message=message,
            provider=provider,
            timeout=deadline_seconds,
            elapsed=elapsed,
            phase="overall",
            endpoint=endpoint,
            attempts=attempts,
        )


# ===========================
# ProviderOverloadedError
# ===========================
@dataclass(slots=True)
class ProviderOverloadedError(ModelGatewayError):
    """Provider przeciążony / throttling (np. HTTP 429, throttling SDK).

    Rozszerza ModelGatewayError o szczegóły związane z rate limitami.
    Dzięki temu warstwa wyżej (gateway/rettry/backoff) może podjąć decyzję:
    - jak długo spać (Retry-After, RateLimit-Reset[-After]),
    - czy to limit "miękki" (chwilowe przeciążenie) czy "twardy" (quota wyczerpana),
    - jakie limity/okna obowiązują (per-request, per-tokens, global/bucket).

    Pola dodatkowe:
      limit:         ogólny limit (np. żądań na okno) jeśli da się wyczytać,
      remaining:     ile pozostało (jeśli da się wyczytać),
      window:        nazwa/rozmiar okna limitowania (np. "1m", "60s", "minute"),
      reset_at:      znacznik czasu (epoch sekundy), kiedy limit się zresetuje,
      reset_after:   czas w sekundach do resetu (jeśli nagłówek podaje względny),
      scope:         scope/polityka (np. "requests", "tokens", "write", "read"),
      bucket:        identyfikator kubełka limitów (np. "org_123", "project_foo"),
      region:        region/datacenter (jeśli provider raportuje),
      reason:        krótki powód/etykieta (np. "rate_limited", "burst", "quota_exhausted").

    Metody pomocnicze:
      - suggested_sleep(attempts, base, cap): oblicza zalecany czas snu,
        preferując Retry-After/Reset, a w braku: exponential backoff.
      - is_hard_limit(): heurystyka rozróżnienia "quota exhausted" vs "burst".
    """

    limit: int | None = None
    remaining: int | None = None
    window: str | None = None
    reset_at: float | None = None        # epoch seconds (UTC)
    reset_after: float | None = None      # sekundy (relative)
    scope: str | None = None              # np. "requests", "tokens"
    bucket: str | None = None             # np. "org_xxx", "project_yyy"
    region: str | None = None
    reason: str | None = None             # np. "rate_limited" | "quota_exhausted"


    def __str__(self) -> str:
        """Zwraca szczegółową, czytelną reprezentację błędu przeciążenia.

        Format wyjściowy jest zoptymalizowany pod kątem logowania i szybkiej
        diagnostyki problemów z limitami zapytań (rate limiting). Zawiera
        wszystkie dostępne informacje z nagłówków `RateLimit-*` i `Retry-After`,
        takie jak pozostałe żądania, czas do resetu limitu i zakres (scope).

        Returns
        -------
            Sformatowany string reprezentujący błąd, np.:
            "Rate limited [provider=openai] [status=429] [remaining=0] [reset_after=15.123s]"

        """
        parts = [self.message or "Provider overloaded / throttled"]
        if self.provider:
            parts.append(f"[provider={self.provider}]")
        if self.status_code is not None:
            parts.append(f"[status={self.status_code}]")
        if self.request_id:
            parts.append(f"[request_id={self.request_id}]")

        # Preferuj jawne informacje o oknie/resetach
        if self.remaining is not None:
            parts.append(f"[remaining={self.remaining}]")
        if self.limit is not None:
            parts.append(f"[limit={self.limit}]")
        if self.window:
            parts.append(f"[window={self.window}]")
        if self.reset_after is not None:
            parts.append(f"[reset_after={self.reset_after:.3f}s]")
        if self.reset_at is not None:
            iso = datetime.fromtimestamp(self.reset_at, tz=UTC).isoformat()
            parts.append(f"[reset_at={iso}]")
        if self.retry_after is not None:
            parts.append(f"[retry_after={self.retry_after:.2f}s]")
        if self.scope:
            parts.append(f"[scope={self.scope}]")
        if self.bucket:
            parts.append(f"[bucket={self.bucket}]")
        if self.region:
            parts.append(f"[region={self.region}]")
        if self.reason:
            parts.append(f"[reason={self.reason}]")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Parsowanie nagłówków limitów: wspieramy zarówno IETF "RateLimit-*"
    # (draft RFC), jak i popularne warianty vendorowe (OpenAI/Anthropic/…)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _parse_epoch(value: Any) -> float | None:
        """Próbujemy zinterpretować wartość jako epoch sekundy.
        Jeśli jest to ISO8601, nie parsujemy tutaj (zachowujemy prostotę) preferujemy
        nagłówki typu "reset-after". W razie potrzeby można dodać parser ISO.
        Heurystyka: jeśli wartość jest bardzo duża (>10_000_000), traktujemy jako ms.
        """  # noqa: D205
        try:
            v = float(value)
            if v > 10_000_000:  # heurystyka: to raczej ms
                return v / 1000.0
            return v
        except Exception:
            return None


    # --- Sekcja parsowania nagłówków  ---

    @classmethod
    def _parse_retry_after(cls, h: dict[str, str]) -> dict[str, Any]:
        """Parsuje nagłówek 'Retry-After'."""
        ra = h.get("retry-after")
        if not ra:
            return {}

        ra_val = cls._parse_float(ra)
        if ra_val is not None:
            return {"retry_after": max(0.0, ra_val)}

        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(ra)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return {"retry_after": max(0.0, (dt - datetime.now(UTC)).total_seconds())}
        except Exception:
            return {}

    @classmethod
    def _parse_ietf_ratelimit(cls, h: dict[str, str]) -> dict[str, Any]:
        """Parsuje nagłówki zgodne z draftem IETF 'RateLimit-*'."""
        out = {}
        if "ratelimit-remaining" in h:
            out["remaining"] = cls._parse_int(h.get("ratelimit-remaining"))
        if "ratelimit-limit" in h:
            out["limit"] = cls._parse_int(h.get("ratelimit-limit"))
        if "ratelimit-reset" in h:
            out["reset_after"] = cls._parse_float(h.get("ratelimit-reset"))
        return out

    @classmethod
    def _parse_openai_ratelimit(cls, h: dict[str, str]) -> dict[str, Any]:
        """Parsuje nagłówki w stylu OpenAI 'x-ratelimit-*'."""
        rem_req = cls._parse_int(h.get("x-ratelimit-remaining-requests"))
        rem_tok = cls._parse_int(h.get("x-ratelimit-remaining-tokens"))

        if rem_req is None and rem_tok is None:
            return {}

        # Wybieramy "ostrzejsze" ograniczenie (mniej pozostałych prób)
        if rem_tok is not None and (rem_req is None or rem_tok < rem_req):
            return {
                "remaining": rem_tok,
                "limit": cls._parse_int(h.get("x-ratelimit-limit-tokens")),
                "reset_after": cls._parse_float(h.get("x-ratelimit-reset-tokens")),
                "scope": "tokens",
            }
        else:
            return {
                "remaining": rem_req,
                "limit": cls._parse_int(h.get("x-ratelimit-limit-requests")),
                "reset_after": cls._parse_float(h.get("x-ratelimit-reset-requests")),
                "scope": "requests",
            }

    @classmethod
    def _parse_anthropic_ratelimit(cls, h: dict[str, str]) -> dict[str, Any]:
        """Parsuje nagłówki w stylu Anthropic."""
        rem_req = cls._parse_int(h.get("anthropic-ratelimit-requests-remaining"))
        if rem_req is None:
            return {}

        return {
            "remaining": rem_req,
            "limit": cls._parse_int(h.get("anthropic-ratelimit-requests-limit")),
            "reset_after": cls._parse_float(h.get("anthropic-ratelimit-requests-reset")),
            "scope": "requests",
        }

    @classmethod
    def _get_request_id(cls, h: dict[str, str]) -> dict[str, Any]:
        """Wyszukuje ID żądania w popularnych nagłówkach."""
        req_id = (
            h.get("x-request-id")
            or h.get("request-id")
            or h.get("x-amzn-requestid")
            or h.get("x-amzn-request-id")
        )
        return {"request_id": req_id} if req_id else {}

    @classmethod
    def _parse_rate_limit_headers(cls, headers: dict[str, str] | None) -> dict[str, Any]:
        """Normalizuje znane nagłówki limitowania do wspólnych pól.

        Ta metoda orkiestruje wywołanie mniejszych, wyspecjalizowanych
        parserów w zdefiniowanej kolejności, scalając ich wyniki.
        Dzięki temu jej złożoność poznawcza jest bardzo niska.
        """
        if not headers:
            return {}

        h = {k.lower(): v for k, v in headers.items()}
        # Wywołujemy parsery w ustalonej kolejności.
        # Tzn. kolejność ma znaczenie: bardziej specyficzne (vendorowe)
        # parsery powinny być pierwsze, aby mogły nadpisać ogólne.
        # Zaczynamy od pustego słownika i aktualizujemy go wynikami
        # kolejnych parserów.
        parsed_data = {}
        parsed_data.update(cls._parse_ietf_ratelimit(h))
        parsed_data.update(cls._parse_anthropic_ratelimit(h))
        parsed_data.update(cls._parse_openai_ratelimit(h)) # OpenAI nadpisze inne, bo jest najbardziej szczegółowy
        parsed_data.update(cls._parse_retry_after(h)) # Retry-After ma najwyższy priorytet
        parsed_data.update(cls._get_request_id(h))

        return parsed_data

    @classmethod
    def from_httpx_429(
        cls,
        exc: httpx.HTTPStatusError,  # noqa: F821 # type: ignore
        *,
        provider: str,
        message: str = "Rate limited / overloaded",
        reason: str | None = None,
        endpoint: str | None = None,
    ) -> ProviderOverloadedError:
        """Fabryka do mapowania httpx.HTTPStatusError 429 -> ProviderOverloaded.

        Pobiera standardowe „RateLimit-*” i vendorowe nagłówki, ustawia retry_after/reset.
        """
        import httpx  # lazy import
        if not isinstance(exc, httpx.HTTPStatusError):
            raise TypeError(
                f"from_httpx_429 oczekuje httpx.HTTPStatusError, a otrzymało {type(exc).__name__}"
            )

        hdrs = dict(exc.response.headers or {})
        parsed = cls._parse_rate_limit_headers(hdrs)

        retry_after = parsed.get("retry_after")
        reset_after = parsed.get("reset_after")
        now = time.time()

        # preferuj retry_after; jeżeli nie ma — użyj reset_after jako względnego
        reset_at = None
        if reset_after is not None:
            reset_at = now + max(0.0, float(reset_after))

        return cls(
            message=message,
            provider=provider,
            status_code=429,
            request_id=parsed.get("request_id"),
            retry_after=retry_after,
            details=_safe_try_json(exc),
            raw=exc.response,
            limit=parsed.get("limit"),
            remaining=parsed.get("remaining"),
            window=parsed.get("window"),
            reset_at=reset_at,
            reset_after=reset_after,
            scope=parsed.get("scope"),
            bucket=None,
            region=exc.response.headers.get("x-amzn-region") if hasattr(exc.response, "headers") else None,
            reason=reason or "rate_limited",
        )

    # -------------------------
    # Heurystyki i rekomendacje
    # -------------------------

    def is_hard_limit(self) -> bool:
            """Określa, czy przekroczony limit jest prawdopodobnie "twardy".

            Ta metoda używa heurystyk do rozróżnienia między dwoma typami
            przekroczenia limitów:
            - **Miękki limit (Soft Limit)**: Zwykle chwilowe przeciążenie lub
            przekroczenie limitu "burst". Ponowienie próby po krótkim
            oczekiwaniu ma duże szanse powodzenia.
            - **Twardy limit (Hard Limit)**: Zwykle oznacza wyczerpanie stałej
            kwoty (np. miesięcznego budżetu, limitu tokenów na minutę).
            Natychmiastowe ponowienie próby prawie na pewno się nie powiedzie.

            Logika opiera się na analizie pola `reason` (jeśli dostawca je zwrócił)
            oraz wartości `remaining`.

            Returns:
            -------
                True, jeśli limit jest uznawany za "twardy" (np. wyczerpana kwota).
                False, jeśli jest to prawdopodobnie chwilowe przeciążenie.

            Example:
            -------
                Użycie w zaawansowanej logice ponawiania prób:

                .. code-block:: python

                    except ProviderOverloadedError as e:
                        if e.is_hard_limit():
                            # Nie ponawiaj, od razu zwróć błąd lub umieść
                            # zadanie w kolejce do wykonania w przyszłości.
                            logger.error("Osiągnięto twardy limit API. Przerywanie.")
                            raise
                        else:
                            # To chwilowy problem, poczekaj i spróbuj ponownie.
                            await asyncio.sleep(e.suggested_sleep())

            """
            if self.reason and "quota" in self.reason.lower():
                return True
            # Jeśli `remaining` jest równe 0, a nie mamy informacji, kiedy limit
            # zostanie zresetowany, bezpieczniej jest założyć, że jest to twardy limit.
            if self.remaining == 0 and self.reset_after is None and self.reset_at is None:
                return True
            return False

# wewnątrz klasy ProviderOverloadedError

    def suggested_sleep(self, *, attempts: int = 0, base: float = 1.0, cap: float = 60.0, jitter: bool = True) -> float:
        """Zwraca rekomendowany czas uśpienia (w sekundach) przed ponowną próbą.

        Logika wyboru czasu oczekiwania jest oparta na priorytetach:
        1. Użyj wartości `Retry-After` z nagłówka, jeśli jest dostępna.
        2. Użyj wartości `RateLimit-Reset`, jeśli jest dostępna.
        3. W przeciwnym razie, zastosuj strategię exponential backoff z losowym
           jitterem, aby uniknąć efektu "thundering herd".

        Args:
        ----
            attempts: Numer bieżącej próby ponowienia (zaczynając od 0).
            base: Bazowy czas oczekiwania dla exponential backoff.
            cap: Maksymalny czas oczekiwania.
            jitter: Czy zastosować losowy jitter do czasu oczekiwania.

        Returns:
        -------
            Sugerowany czas oczekiwania w sekundach.

        """
        # retry_after, jeśli provider podał
        if self.retry_after is not None:
            return max(0.0, self.retry_after)

        # Czas do resetu limitu, jeśli jest znany
        now = time.time()
        if self.reset_after is not None:
            return max(0.0, self.reset_after)
        if self.reset_at is not None:
            return max(0.0, self.reset_at - now)

        # Fallback na exponential backoff
        delay = min(cap, base * (2.0 ** attempts))

        if jitter:
            try:
                # Używamy modułu `secrets` do generowania bezpiecznej losowości.
                # `secrets.SystemRandom().uniform()` działa tak samo jak `random.uniform()`,
                # ale używa kryptograficznie bezpiecznego generatora.
                delay = secrets.SystemRandom().uniform(0.0, delay)
            except Exception as e:
                logger.warning(
                    "Nie udało się zastosować jittera do czasu oczekiwania. "
                    f"Użycie stałego opóźnienia: {delay:.2f}s. Błąd: {e}"
                )

        return delay


# Helper: bezpiecznie wyciąga JSON/text z httpx.Response (do details)
def _safe_try_json(exc: Any) -> Any:
    try:
        resp = getattr(exc, "response", None)
        if resp is None:
            return None
        try:
            return resp.json()
        except Exception:
            return resp.text
    except Exception:
        return None


# ===========================
# ProviderServerError (5xx)
# ===========================
@dataclass
class ProviderServerError(ModelGatewayError):
    """Błąd po stronie serwera providera (5xx lub ekwiwalent SDK).

    Po co osobna klasa?
      - Rozróżnia awarie *u providera* (5xx) od błędów klienta/konfiguracji,
      - Niesie kontekst do decyzji o retry/backoff (retryable?, retry-after, rodzina statusu),
      - Ułatwia spójne logowanie/alertowanie (status, request_id, szczegóły odpowiedzi).

    Dodatkowe pola:
      status_family : rodzina statusu HTTP (np. 500, 502, 503, 504) - ułatwia strategię retry,
      endpoint      : adres/operacja, na którą zgłaszaliśmy żądanie,
      retryable     : heurystyka, czy warto spróbować ponownie (domyślnie True dla 502/503/504),
      upstream      : (opcjonalnie) nazwa usługi/regionu po stronie providera, jeśli raportuje,
      reason        : krótki powód/etykieta (np. "bad_gateway", "unavailable", "timeout").
    """

    status_family: int | None = None
    endpoint: str | None = None
    retryable: bool | None = None
    upstream: str | None = None
    reason: str | None = None

    def __str__(self) -> str:
        """Zwraca szczegółową, czytelną reprezentację błędu serwera dostawcy.

        Format wyjściowy jest zoptymalizowany pod kątem logowania i szybkiej
        diagnostyki błędów 5xx. Zawiera kluczowe informacje kontekstowe,
        takie jak status, endpoint i informację, czy ponowienie próby
        jest zalecane (`retryable`).

        Returns
        -------
            Sformatowany string reprezentujący błąd, np.:
            "Provider 5xx server error [provider=openai] [status=503] [retryable=True]"

        """
        parts = [self.message or "Provider server error"]
        if self.provider:
            parts.append(f"[provider={self.provider}]")
        if self.status_code is not None:
            parts.append(f"[status={self.status_code}]")
        if self.status_family is not None:
            parts.append(f"[family={self.status_family}]")
        if self.request_id:
            parts.append(f"[request_id={self.request_id}]")
        if self.endpoint:
            parts.append(f"[endpoint={self.endpoint}]")
        if self.retry_after is not None:
            parts.append(f"[retry_after={self.retry_after:.2f}s]")
        if self.retryable is not None:
            parts.append(f"[retryable={self.retryable}]")
        if self.upstream:
            parts.append(f"[upstream={self.upstream}]")
        if self.reason:
            parts.append(f"[reason={self.reason}]")
        return " ".join(parts)

    # -------- Fabryki / mapowanie 5xx --------

    @staticmethod
    def _parse_retry_after(headers: dict[str, str]) -> float | None:
        """Parser 'Retry-After' (sekundy lub HTTP-date). Zwraca sekundy (float) albo None."""
        if not headers:
            return None
        h = {k.lower(): v for k, v in headers.items()}
        ra = h.get("retry-after")
        if not ra:
            return None
        # próba liczby (sekundy)
        try:
            return max(0.0, float(ra))
        except Exception:
            # HTTP-date -> konwersja na sekundy do przyszłości
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(ra)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return max(0.0, (dt - datetime.now(UTC)).total_seconds())
            except Exception:
                return None

    @staticmethod
    def _safe_details_from_httpx(exc: Any) -> Any:
        """Bezpiecznie wyciąga JSON/tekst z httpx.Response do `details`."""
        try:
            resp = getattr(exc, "response", None)
            if resp is None:
                return None
            try:
                return resp.json()
            except Exception:
                return resp.text
        except Exception:
            return None

    @classmethod
    @classmethod
    def from_httpx_5xx(
        cls,
        exc: httpx.HTTPStatusError,  # noqa: F821 # type: ignore
        *,
        provider: str,
        endpoint: str | None = None,
        message: str = "Provider 5xx server error",
        request_id_header: str = "x-request-id",
        reason: str | None = None,
    ) -> "ProviderServerError":  # noqa: UP037
        """Tworzy instancję ProviderServerError na podstawie błędu HTTP 5xx z `httpx`.

        Ta metoda fabryczna parsuje odpowiedź błędu, wyciągając kluczowe
        informacje diagnostyczne, takie jak status, ID żądania i nagłówek
        `Retry-After`. Ustawia również heurystykę `retryable` w zależności
        od kodu statusu.

        Args:
        ----
            exc: Wyjątek `httpx.HTTPStatusError` do przetworzenia.
            provider: Identyfikator dostawcy (np. "openai").
            endpoint: Adres URL, do którego kierowane było zapytanie.
            message: Niestandardowy komunikat błędu.
            request_id_header: Nazwa nagłówka zawierającego ID żądania.
            reason: Niestandardowy powód błędu.

        Returns:
        -------
            Nowa instancja `ProviderServerError` z wypełnionymi polami.

        Raises:
        ------
            TypeError: Jeśli przekazany wyjątek `exc` nie jest typu
                `httpx.HTTPStatusError`.

        """
        import httpx  # lazy import
        if not isinstance(exc, httpx.HTTPStatusError):
            raise TypeError(
                f"from_httpx_5xx oczekuje httpx.HTTPStatusError, a otrzymało {type(exc).__name__}"
            )

        resp = exc.response
        status = resp.status_code
        headers = dict(resp.headers or {})
        req_id = (
            headers.get(request_id_header.lower())
            or headers.get("x-amzn-requestid")
            or headers.get("x-amzn-request-id")
        )
        retry_after = cls._parse_retry_after(headers)
        family = (status // 100) * 100 if status is not None else None

        # Heurystyka: błędy 502, 503, 504 są zazwyczaj przejściowe i można
        # je ponowić. Błąd 500 jest często błędem trwałym.
        if status in (502, 503, 504):
            retryable = True
        elif status == 500:
            retryable = False
        else:
            retryable = None  # Nieznany błąd 5xx, decyzja o ponowieniu jest niepewna.

        return cls(
            message=message,
            provider=provider,
            status_code=status,
            status_family=family,
            request_id=req_id,
            retry_after=retry_after,
            details=cls._safe_details_from_httpx(exc),
            raw=resp,
            endpoint=endpoint,
            retryable=retryable,
            upstream=headers.get("via") or headers.get("server"),
            reason=reason,
        )
    @classmethod
    def from_response(
        cls,
        *,
        provider: str,
        status_code: int | None,
        message: str,
        endpoint: str | None = None,
        request_id: str | None = None,
        retry_after: float | None = None,
        details: Any = None,
        raw: Any = None,
        retryable: bool | None = None,
        reason: str | None = None,
        upstream: str | None = None,
    ) -> "ProviderServerError":  # noqa: UP037
        """Tworzy instancję ProviderServerError z niestandardowych źródeł.

        Ta uniwersalna metoda fabryczna jest przeznaczona do użycia w sytuacjach,
        gdy błąd pochodzi ze źródeł innych niż `httpx`, np. z klienta SDK
        (jak `boto3` dla AWS Bedrock).

        Jeśli parametr `retryable` nie zostanie jawnie podany, metoda
        automatycznie wywnioskuje jego wartość na podstawie `status_code`.

        Args:
        ----
            provider: Identyfikator dostawcy.
            status_code: Kod statusu HTTP błędu.
            message: Niestandardowy komunikat błędu.
            endpoint: Adres URL, do którego kierowane było zapytanie.
            request_id: Identyfikator żądania.
            retry_after: Sugerowany czas oczekiwania przed ponowieniem.
            details: Dodatkowe szczegóły błędu.
            raw: Surowy obiekt błędu lub odpowiedzi.
            retryable: Jawne określenie, czy błąd jest ponawialny.
            reason: Niestandardowy powód błędu.
            upstream: Nazwa usługi upstream, jeśli jest znana.

        Returns:
        -------
            Nowa instancja `ProviderServerError`.

        """
        family = (status_code // 100) * 100 if status_code is not None else None
        # Heurystyka retryable na podstawie status_code.
        # Działa tylko wtedy, gdy `retryable` nie zostało jawnie przekazane.
        if retryable is None and status_code is not None:
            if status_code in (502, 503, 504):
                retryable = True
            elif status_code == 500:
                retryable = False
            # W przeciwnym razie `retryable` pozostaje None (niepewne)

        return cls(
            message=message,
            provider=provider,
            status_code=status_code,
            status_family=family,
            request_id=request_id,
            retry_after=retry_after,
            details=details,
            raw=raw,
            endpoint=endpoint,
            retryable=retryable,
            reason=reason,
            upstream=upstream,
        )
    # -------- Rekomendacje retry / backoff --------
    def suggested_sleep(
        self,
        *,
        attempts: int = 0,
        base: float = 1.0,
        cap: float = 60.0,
        jitter: bool = True,
    ) -> float:
        """Sugeruje optymalny czas oczekiwania (w sekundach) przed ponowną próbą.

        Implementuje strategię "fail smart", która najpierw respektuje
        instrukcje serwera, a w razie ich braku stosuje sprawdzoną
        strategię exponential backoff.

        Logika wyboru czasu oczekiwania:
        1. Jeśli serwer zwrócił nagłówek `Retry-After`, jego wartość jest
           używana z najwyższym priorytetem.
        2. W przeciwnym razie, obliczany jest czas oczekiwania za pomocą
           algorytmu exponential backoff z losowym jitterem, aby uniknąć
           efektu "thundering herd".

        Args:
        ----
            attempts: Numer bieżącej próby ponowienia (zaczynając od 0).
            base: Bazowy czas oczekiwania dla exponential backoff (w sekundach).
            cap: Maksymalny czas oczekiwania (w sekundach).
            jitter: Czy zastosować losowy "full jitter" do czasu oczekiwania.

        Returns:
        -------
            Sugerowany czas oczekiwania w sekundach.

        """
        if self.retry_after is not None:
            return max(0.0, self.retry_after)

        delay = min(cap, base * (2.0 ** attempts))

        if jitter:
            try:
                # Używamy kryptograficznie bezpiecznego generatora.
                delay = secrets.SystemRandom().uniform(0.0, delay)
            except Exception as e:
                logger.warning(
                    "Nie udało się zastosować jittera do czasu oczekiwania. "
                    f"Użycie stałego opóźnienia: {delay:.2f}s. Błąd: {e}"
                )

        return delay

    def should_retry(self) -> bool:
        """Określa, czy ponowienie próby dla tego błędu ma sens.

        Metoda ta hermetyzuje heurystykę decydującą, czy błąd serwera
        jest prawdopodobnie przejściowy (i warto go ponowić), czy trwały.

        Logika decyzyjna:
        - Jeśli pole `retryable` zostało jawnie ustawione (np. przez metodę
          fabryczną), jego wartość jest decydująca.
        - W przeciwnym razie, zakłada się, że błędy 502, 503 i 504 są
          przejściowe i można je ponowić.
        - Błąd 500 jest traktowany jako trwały (nie ponawiać).
        - Inne, nieznane błędy 5xx są ostrożnie traktowane jako ponawialne.

        Returns
        -------
            True, jeśli ponowienie próby jest zalecane. W przeciwnym razie False.

        """
        if self.retryable is not None:
            return self.retryable

        if self.status_code in (502, 503, 504):
            return True
        if self.status_code == 500:
            return False

        # Domyślnie, dla nieznanych błędów 5xx, ostrożnie pozwalamy na ponowienie.
        return True


# ===========================
# TokenLimitExceededError
# ===========================
@dataclass(slots=True)
class TokenLimitExceededError(ModelGatewayError):
    """Wyjątek rzucany, gdy zapytanie przekracza limit tokenów modelu.

    Ten błąd sygnalizuje, że suma tokenów w zapytaniu (prompt) i/lub
    oczekiwanej odpowiedzi (`max_tokens`) przekracza maksymalny rozmiar
    okna kontekstowego obsługiwanego przez model.

    Attributes
    ----------
        model: Identyfikator modelu, którego dotyczy limit.
        context_window: Maksymalny rozmiar okna kontekstowego modelu.
        prompt_tokens: Liczba tokenów w zapytaniu.
        requested_output: Żądana liczba tokenów w odpowiedzi.
        overflow: O ile tokenów przekroczono limit (jeśli można to obliczyć).
        strategy: Sugerowana strategia naprawcza (np. "truncate_messages").
        tips: Czytelna dla człowieka wskazówka, jak rozwiązać problem.

    """

    model: str | None = None
    context_window: int | None = None
    prompt_tokens: int | None = None
    completion_limit: int | None = None
    requested_output: int | None = None
    overflow: int | None = None
    strategy: str | None = None
    tips: str | None = None

    def __str__(self) -> str:
        """Zwraca szczegółową, czytelną reprezentację błędu limitu tokenów."""
        parts = [self.message or "Token limit exceeded"]
        if self.provider:
            parts.append(f"[provider={self.provider}]")
        if self.model:
            parts.append(f"[model={self.model}]")
        if self.context_window:
            parts.append(f"[context_window={self.context_window}]")
        if self.prompt_tokens:
            parts.append(f"[prompt_tokens={self.prompt_tokens}]")
        if self.overflow:
            parts.append(f"[overflow={self.overflow}]")
        if self.strategy:
            parts.append(f"[strategy={self.strategy}]")
        return " ".join(parts)

    def suggest_truncation(self) -> int | None:
        """Sugeruje, o ile tokenów należy skrócić zapytanie.

        Oblicza, o ile tokenów zapytanie jest za długie, aby zmieścić się
        w oknie kontekstowym, uwzględniając żądaną długość odpowiedzi.

        Returns
        -------
            Sugerowana liczba tokenów do usunięcia z zapytania, lub None,
            jeśli nie można tego obliczyć.

        """
        if self.context_window is None or self.prompt_tokens is None:
            return None

        requested_output = self.requested_output or 0
        available_for_prompt = self.context_window - requested_output

        return max(0, self.prompt_tokens - available_for_prompt)

    def recommend_strategy(self) -> tuple[str, str]:
        """Rekomenduje strategię i wskazówkę, jak rozwiązać problem limitu.

        Returns
        -------
            Krotka zawierająca (nazwa_strategii, czytelna_wskazówka).

        """
        truncation_needed = self.suggest_truncation()
        if truncation_needed and truncation_needed > 0:
            return (
                "truncate_messages",
                f"Zredukuj zapytanie o co najmniej {truncation_needed} tokenów. "
                "Rozważ usunięcie starszych wiadomości lub skrócenie kontekstu z RAG.",
            )

        if self.requested_output and self.context_window and self.prompt_tokens:
            available_for_output = self.context_window - self.prompt_tokens
            if available_for_output > 0 and self.requested_output > available_for_output:
                return (
                    "reduce_max_tokens",
                    f"Zmniejsz `max_tokens` z {self.requested_output} do wartości nie większej niż {available_for_output}.",
                )

        return ("summarize", "Spróbuj skrócić lub streścić treść zapytania.")

    @classmethod
    def from_provider_payload(
        cls,
        *,
        provider: str,
        message: str = "Token/context limit exceeded",
        model: str | None = None,
        context_window: int | None = None,
        prompt_tokens: int | None = None,
        requested_output: int | None = None,
        completion_limit: int | None = None,
        details: Any = None,
        raw: Any = None,
        request_id: str | None = None,
    ) -> "TokenLimitExceededError":  # noqa: UP037
        """Tworzy instancję błędu na podstawie danych z logiki aplikacji lub SDK."""
        overflow = None
        if context_window is not None and prompt_tokens is not None:
            overflow = max(0, (prompt_tokens + (requested_output or 0)) - context_window)

        instance = cls(
            message=message, provider=provider, model=model,
            context_window=context_window, prompt_tokens=prompt_tokens,
            requested_output=requested_output, completion_limit=completion_limit,
            overflow=overflow, details=details, raw=raw, request_id=request_id,
        )
        instance.strategy, instance.tips = instance.recommend_strategy()
        return instance

    @classmethod
    def from_httpx_response(
        cls,
        resp: httpx.Response,  # noqa: F821 # type: ignore
        *,
        provider: str,
        message: str = "Token/context limit exceeded",
        model: str | None = None,
        request_id_header: str = "x-request-id",
    ) -> "TokenLimitExceededError":  # noqa: UP037
        """Tworzy instancję błędu, próbując sparsować odpowiedź błędu HTTP."""
        import httpx  # lazy import
        if not isinstance(resp, httpx.Response):
            raise TypeError(f"from_httpx_response oczekuje httpx.Response, a otrzymało {type(resp).__name__}")

        details: Any = None
        try:
            details = resp.json()
        except Exception:
            details = resp.text

        ctx, pt, req_out, comp_lim = None, None, None, None
        if isinstance(details, dict):
            ctx = details.get("context_window") or details.get("max_context")
            pt = details.get("prompt_tokens") or details.get("input_tokens")
            req_out = details.get("requested_output") or details.get("max_tokens")
            comp_lim = details.get("completion_limit")

        return cls.from_provider_payload(
            provider=provider, message=message, model=model,
            context_window=ctx if isinstance(ctx, int) else None,
            prompt_tokens=pt if isinstance(pt, int) else None,
            requested_output=req_out if isinstance(req_out, int) else None,
            completion_limit=comp_lim if isinstance(comp_lim, int) else None,
            details=details, raw=resp,
            request_id=resp.headers.get(request_id_header.lower()),
        )


#---------------------------------------------------------------------------
# Rola komunikatu + model wiadomości
# ---------------------------------------------------------------------------

class Role(str, Enum):
    """Definiuje standardowe role uczestników w konwersacji z modelem LLM.

    Enum ten zapewnia spójny i jednoznaczny zestaw ról, które są używane
    w obiekcie `LLMMessage` do strukturyzowania dialogu. Dziedziczenie po
    `str` sprawia, że wartości enuma mogą być bezpośrednio używane jako stringi.

    Attributes
    ----------
        SYSTEM: Rola dla instrukcji systemowych. Wiadomości te ustawiają
            kontekst, osobowość lub zasady, którymi ma kierować się model
            (np. "Jesteś pomocnym asystentem.").
        USER: Rola dla wiadomości pochodzących od użytkownika końcowego.
            Reprezentuje zapytania, polecenia lub odpowiedzi człowieka.
        ASSISTANT: Rola dla odpowiedzi wygenerowanych przez model LLM.
            Może zawierać zwykły tekst lub, w zaawansowanych scenariuszach,
            prośby o wywołanie narzędzi (tool calls).
        TOOL: Rola dla wiadomości zawierających wynik działania narzędzia.
            Jest to odpowiedź zwrotna do modelu, informująca go o rezultacie
            akcji, o którą prosił.

    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class LLMMessage:
    """Reprezentuje pojedynczą wiadomość w rozmowie.

    Pola:
      role:    rola nadawcy (system/user/assistant/tool),
      content: treść (czysty tekst; dla „tool” zwykle JSON -> str).

    Uwaga:
      - modelowane minimalistycznie; konkretni providerzy mogą rozszerzać
        ten format (np. części multimodalne), ale base API trzyma tekst.
    """

    role: str
    content: str

    def as_dict(self) -> dict[str, str]:
        """Lekka reprezentacja słownikowa (przydatna do logów/serializacji)."""
        return {"role": self.role, "content": self.content}

    @staticmethod
    def system(text: str) -> "LLMMessage":  # noqa: UP037
        """Tworzy wiadomość o roli 'system'.

        Metoda fabryczna do wygodnego tworzenia instrukcji systemowych,
        które ustawiają kontekst lub zachowanie modelu.

        Args:
        ----
            text: Treść instrukcji systemowej.

        Returns:
        -------
            Nowa instancja `LLMMessage` z rolą `Role.SYSTEM`.

        Example:
        -------
            >>> instruction = LLMMessage.system("Odpowiadaj zawsze po polsku.")

        """
        return LLMMessage(role=Role.SYSTEM.value, content=text)

    @staticmethod
    def user(text: str) -> "LLMMessage":  # noqa: UP037
        """Tworzy wiadomość o roli 'user'.

        Metoda fabryczna do tworzenia wiadomości reprezentujących
        zapytanie lub odpowiedź od użytkownika końcowego.

        Args:
        ----
            text: Treść zapytania użytkownika.

        Returns:
        -------
            Nowa instancja `LLMMessage` z rolą `Role.USER`.

        Example:
        -------
            >>> query = LLMMessage.user("Jaka jest pogoda w Warszawie?")

        """
        return LLMMessage(role=Role.USER.value, content=text)

    @staticmethod
    def assistant(text: str) -> "LLMMessage":  # noqa: UP037
        """Tworzy wiadomość o roli 'assistant'.

        Metoda fabryczna do tworzenia wiadomości reprezentujących
        odpowiedź wygenerowaną przez model LLM.

        Args:
        ----
            text: Treść odpowiedzi modelu.

        Returns:
        -------
            Nowa instancja `LLMMessage` z rolą `Role.ASSISTANT`.

        Example:
        -------
            >>> response = LLMMessage.assistant("Pogoda w Warszawie jest słoneczna.")

        """
        return LLMMessage(role=Role.ASSISTANT.value, content=text)

    @staticmethod
    def tool(text: str) -> "LLMMessage":  # noqa: UP037
        """Tworzy wiadomość o roli 'tool'.

        Metoda fabryczna do tworzenia wiadomości zawierających wynik
        działania zewnętrznego narzędzia (np. API), przekazywany z powrotem
        do modelu.

        Args:
        ----
            text: Treść wyniku narzędzia (często w formacie JSON jako string).

        Returns:
        -------
            Nowa instancja `LLMMessage` z rolą `Role.TOOL`.

        Example:
        -------
            >>> tool_result = LLMMessage.tool('{"temperature": 25, "unit": "celsius"}')

        """
        return LLMMessage(role=Role.TOOL.value, content=text)

# ---------------------------------------------------------------------------
# Parametry chatu + usage + chunk do streamingu
# ---------------------------------------------------------------------------
def _clamp(v: float, lo: float, hi: float) -> float:
    """Ogranicza wartość `v` do zakresu [lo, hi] w sposób idiomatyczny.

    Ta implementacja wykorzystuje wbudowane funkcje `min` i `max` do
    osiągnięcia tego samego rezultatu w zwięzły i wydajny sposób.

    Args:
    ----
        v: Wartość do ograniczenia.
        lo: Dolna granica zakresu.
        hi: Górna granica zakresu.

    Returns:
    -------
        Wartość `v` ograniczona do zakresu [lo, hi].

    """
    return max(lo, min(v, hi))


@dataclass(slots=True)
class ChatParams:
    """Parametry generacji dla modeli czatowych.

    Pola:
      max_tokens:   limit tokenów odpowiedzi (0 => provider default),
      temperature:  stopień kreatywności (0..2 zazwyczaj); clamp do [0, 2],
      top_p:        nucleus sampling (0..1); clamp do [0, 1],
      stop:         lista sekwencji stop,
      extra:        dostawca-specyficzne rozszerzenia (np. 'response_format').

    Metody dbają o bezpieczne zakresy (clamp), aby uniknąć błędów po stronie API.
    """

    max_tokens: int = 512
    temperature: float = 0.2
    top_p: float = 1.0
    stop: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> ChatParams:
        """Zwraca skopiowane parametry ze ściętymi wartościami do bezpiecznych zakresów."""
        mt = max(1, int(self.max_tokens)) if self.max_tokens else 0
        return ChatParams(
            max_tokens=mt,
            temperature=float(_clamp(self.temperature, 0.0, 2.0)),
            top_p=float(_clamp(self.top_p, 0.0, 1.0)),
            stop=list(self.stop or []),
            extra=dict(self.extra or {}),
        )


@dataclass(slots=True)
class Usage:
    """Reprezentuje statystyki zużycia tokenów dla pojedynczego wywołania LLM.

    Klasa ta jest używana do zliczania i raportowania, ile tokenów zostało
    przetworzonych w zapytaniu (prompt) i ile zostało wygenerowanych
    w odpowiedzi (completion).

    Attributes
    ----------
        prompt_tokens: Liczba tokenów w wejściowym zapytaniu.
        completion_tokens: Liczba tokenów w wygenerowanej odpowiedzi.

    """

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Oblicza i zwraca całkowitą liczbę przetworzonych tokenów.

        Returns
        -------
            Suma `prompt_tokens` i `completion_tokens`.

        """
        return self.prompt_tokens + self.completion_tokens


@dataclass(slots=True)
class ChatChunk:
    """Reprezentuje pojedynczy fragment danych w strumieniu odpowiedzi od LLM.

    Gdy odpowiedź z modelu jest strumieniowana (streaming), jest ona dzielona
    na mniejsze części, a każda z nich jest enkapsulowana w tej klasie.
    Pozwala to na progresywne renderowanie odpowiedzi w czasie rzeczywistym.

    Attributes
    ----------
        delta: Fragment nowo wygenerowanego tekstu w tej części strumienia.
        finish_reason: Opcjonalny powód zakończenia generowania, wysyłany
            zazwyczaj w ostatnim fragmencie (np. "stop" dla naturalnego
            zakończenia, "length" dla osiągnięcia `max_tokens`).
        usage: Opcjonalne, narastające statystyki zużycia tokenów, jeśli
            dostawca raportuje je w trakcie strumieniowania.

    """

    delta: str
    finish_reason: str | None = None
    usage: Usage | None = None


# ---------------------------------------------------------------------------
# Kontrakt Tokenizatora
# ---------------------------------------------------------------------------

@runtime_checkable
class Tokenizer(Protocol):
    """Definiuje kontrakt dla obiektów zdolnych do zliczania tokenów.

    Klasy implementujące ten protokół dostarczają mechanizm do obliczania,
    ile tokenów zużyje dany tekst lub sekwencja wiadomości. Jest to kluczowe
    do proaktywnego zarządzania limitami kontekstu modeli LLM.

    Example:
    -------
        Implementacja z użyciem biblioteki `tiktoken`:

        .. code-block:: python

            import tiktoken

            class TiktokenTokenizer(Tokenizer):
                def __init__(self, model_name: str = "gpt-4"):
                    self.encoder = tiktoken.encoding_for_model(model_name)

                def count_tokens(self, text: str) -> int:
                    return len(self.encoder.encode(text))

                def count_chat(self, messages: Sequence[LLMMessage]) -> int:
                    # Logika zliczania specyficzna dla formatu chat...
                    ...

    """

    def count_tokens(self, text: str) -> int:
        """Zlicza tokeny w pojedynczym ciągu znaków.

        Args:
        ----
            text: Tekst do przetworzenia.

        Returns:
        -------
            Liczba tokenów.

        """
        raise NotImplementedError

    def count_chat(self, messages: Sequence[LLMMessage]) -> int:
        """Zlicza tokeny w całej sekwencji wiadomości.

        Implementacja tej metody powinna uwzględniać dodatkowe tokeny
        specjalne, które modele dodają między wiadomościami.

        Args:
        ----
            messages: Sekwencja wiadomości do przetworzenia.

        Returns:
        -------
            Całkowita liczba tokenów dla całej konwersacji.

        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Kontrakt Dostawcy LLM
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMProvider(Protocol):
    """Definiuje kontrakt, który muszą spełnić wszyscy dostawcy modeli LLM.

    Protokół ten standaryzuje interfejs do komunikacji z różnymi modelami
    językowymi, zapewniając, że są one wymienne w ramach aplikacji.
    Wymaga implementacji dwóch głównych metod: `chat` (dla pełnych odpowiedzi)
    i `stream` (dla odpowiedzi strumieniowych).
    """

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: ChatParams | None = None,
        tokenizer: Tokenizer | None = None,
        request_id: str | None = None,
    ) -> str:
        """Wysyła zapytanie do modelu i zwraca pełną odpowiedź jako string.

        Args:
        ----
            messages: Sekwencja wiadomości reprezentująca historię konwersacji.
            params: Opcjonalne parametry generacji (temperatura, max_tokens, etc.).
            tokenizer: Opcjonalny tokenizator do weryfikacji limitów przed wysłaniem.
            request_id: Opcjonalny, unikalny identyfikator żądania do celów
                śledzenia (tracing).

        Returns:
        -------
            Wygenerowana przez model odpowiedź w formie tekstowej.

        Raises:
        ------
            ProviderTimeoutError: Gdy zapytanie przekroczyło limit czasu.
            ProviderOverloadedError: Gdy API dostawcy jest przeciążone (rate limit).
            ProviderServerError: W przypadku błędu 5xx po stronie serwera dostawcy.
            TokenLimitExceededError: Gdy zapytanie przekracza limit tokenów modelu.
            ModelGatewayError: W przypadku innych błędów komunikacji lub konfiguracji.

        """
        raise NotImplementedError

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: ChatParams | None = None,
        tokenizer: Tokenizer | None = None,
        request_id: str | None = None,
    ) -> AsyncIterator[ChatChunk]:
        """Wysyła zapytanie i zwraca odpowiedź jako asynchroniczny strumień.

        Implementacje tej metody MUSZĄ używać `yield`, aby zwracać kolejne
        fragmenty (`ChatChunk`) odpowiedzi w miarę ich generowania.

        Args:
        ----
            messages: Sekwencja wiadomości reprezentująca historię konwersacji.
            params: Opcjonalne parametry generacji.
            tokenizer: Opcjonalny tokenizator.
            request_id: Opcjonalny identyfikator żądania.

        Yields:
        ------
             kolejne obiekty `ChatChunk` zawierające fragmenty odpowiedzi.

        Raises:
        ------
            (Te same wyjątki co metoda `chat`).

        """
        # Ten `yield` jest tutaj, aby uczynić tę metodę poprawnym
        # generatorem asynchronicznym. Bez niego, adnotacja typu byłaby
        # niepoprawna.
        yield  # type: ignore[misc]
        raise NotImplementedError

    async def aclose(self) -> None:
        """Opcjonalna metoda do zamykania zasobów, takich jak sesje HTTP.

        Jeśli provider utrzymuje długo żyjące połączenia (np. `httpx.AsyncClient`),
        powinien zaimplementować tę metodę, aby można je było bezpiecznie zamknąć
        podczas zamykania aplikacji.
        """
        # Domyślna implementacja nic nie robi, to jest poprawne dla providerów,
        # którę nie zarządzają zasobami.
        pass


# ---------------------------------------------------------------------------
# Adaptery i Walidatory
# ---------------------------------------------------------------------------

def to_openai_messages(messages: Sequence[LLMMessage]) -> list[dict[str, str]]:
    """Konwertuje ustandaryzowaną sekwencję `LLMMessage` na format OpenAI.

    Ta funkcja pomocnicza tłumaczy wewnętrzny model wiadomości na format
    oczekiwany przez OpenAI Chat Completions API. Obsługuje również
    specyficzne przypadki, takie jak mapowanie roli `TOOL` na `ASSISTANT`
    dla prostych odpowiedzi tekstowych.

    Args:
    ----
        messages: Sekwencja obiektów `LLMMessage` do konwersji.

    Returns:
    -------
        Lista słowników w formacie `[{"role": "...", "content": "..."}, ...]`.

    """
    # Użycie list comprehension jest bardziej zwięzłe i "pythoniczne".
    return [m.as_dict() for m in messages]


def to_anthropic_messages(messages: Sequence[LLMMessage]) -> list[dict[str, str]]:
    """Konwertuje ustandaryzowaną sekwencję `LLMMessage` na format Anthropic.

    Ten adapter tłumaczy wewnętrzny model wiadomości na format oczekiwany
    przez Anthropic Messages API. Kluczową różnicą jest to, że Anthropic
    nie posiada roli `system` - instrukcje systemowe muszą być częścią
    pierwszej wiadomości od użytkownika. Ta funkcja (w przyszłości) powinna
    obsłużyć takie scalanie. Obecna wersja jest uproszczona.

    Args:
    ----
        messages: Sekwencja obiektów `LLMMessage` do konwersji.

    Returns:
    -------
        Lista słowników w formacie `[{"role": "user" | "assistant", "content": "..."}, ...]`.

    """
    # TODO: W pełnej implementacji, jeśli pierwsza wiadomość ma rolę 'system',
    # jej treść powinna zostać połączona z treścią pierwszej wiadomości 'user'.

    out: list[dict[str, str]] = []
    for m in messages:
        # Anthropic akceptuje tylko role 'user' i 'assistant'.
        # Wiadomości systemowe są traktowane jako pochodzące od użytkownika.
        role = "assistant" if m.role == Role.ASSISTANT else "user"
        out.append({"role": role, "content": m.content})
    return out


def validate_conversation(messages: Sequence[LLMMessage]) -> None:
    """Sprawdza, czy sekwencja wiadomości jest poprawna i spójna.

    Ta funkcja waliduje podstawowe reguły, które muszą być spełnione,
    aby konwersacja była akceptowalna przez większość modeli LLM.

    Sprawdzane reguły:
    1. Sekwencja nie może być pusta.
    2. Pierwsza wiadomość musi mieć rolę `SYSTEM` lub `USER`.
    3. Żadna wiadomość nie może mieć pustej treści.
    4. Wszystkie role muszą pochodzić ze zdefiniowanego enuma `Role`.
    5. (Opcjonalnie w przyszłości) Role `USER` i `ASSISTANT` powinny
       występować naprzemiennie.

    Args:
    ----
        messages: Sekwencja obiektów `LLMMessage` do walidacji.

    Raises:
    ------
        ValueError: Jeśli którakolwiek z reguł walidacji nie jest spełniona.

    """
    if not messages:
        raise ValueError("Sekwencja wiadomości nie może być pusta.")

    allowed_roles = {r.value for r in Role}

    if messages[0].role not in (Role.SYSTEM.value, Role.USER.value):
        raise ValueError(
            "Konwersacja musi zaczynać się od wiadomości o roli 'system' lub 'user'."
        )

    for i, msg in enumerate(messages):
        if not msg.content or not msg.content.strip():
            raise ValueError(f"Wiadomość na indeksie {i} ma pustą treść.")

        if msg.role not in allowed_roles:
            raise ValueError(
                f"Wiadomość na indeksie {i} ma nieobsługiwaną rolę: '{msg.role}'."
            )


# ---------------------------------------------------------------------------
# Domyślny, „pusty” tokenizator (noop), jeżeli provider nie posiada własnego
# ---------------------------------------------------------------------------

# src/model_gateway/base.py

# ... (importy i inne klasy) ...
# Upewnij się, że te importy są na górze pliku

# ---------------------------------------------------------------------------
# Domyślny Tokenizator Heurystyczny (Fallback)
# ---------------------------------------------------------------------------

class NoopTokenizer(Tokenizer):
    """Implementacja tokenizatora oparta na prostej heurystyce słów.

    Ta klasa służy jako domyślny, "wystarczająco dobry" tokenizator w sytuacjach,
    gdy precyzyjny tokenizator specyficzny dla danego modelu (np. `tiktoken`)
    nie jest dostępny. Nie jest ona w 100% dokładna, ale dostarcza rozsądnego
    oszacowania do celów weryfikacji limitów.

    Heurystyka:
        Bazując na obserwacjach modeli językowych, przyjmuje się, że
        średnio 4 znaki lub 0.75 słowa odpowiadają jednemu tokenowi.
        Ta implementacja używa wariantu opartego na słowach, który jest
        bardziej odporny na różnice w językach.

    Attributes
    ----------
        WORDS_PER_TOKEN (float): Współczynnik używany do oszacowania liczby tokenów.

    """

    __slots__ = () # Ta klasa nie przechowuje stanu, więc __slots__ jest pusty.

    # Współczynnik oparty na empirycznej analizie modeli OpenAI.
    # 1 token to około 3/4 słowa.
    WORDS_PER_TOKEN: float = 0.75

    def count_tokens(self, text: str) -> int:
        """Szacuje liczbę tokenów w pojedynczym ciągu znaków.

        Args:
        ----
            text: Tekst do przetworzenia.

        Returns:
        -------
            Oszacowana liczba tokenów.

        """
        if not text or not text.strip():
            return 0
        # Proste zliczanie słów jako podstawa do oszacowania tokenów.
        num_words = len(text.split())

        # Obliczenie `words * 4 / 3` jest matematycznie równoważne
        # `words / 0.75`, ale unika dzielenia przez liczbę zmiennoprzecinkową,
        # co jest często minimalnie wydajniejsze i bardziej precyzyjne.
        estimated_tokens = (num_words * 4) // 3

        # Zawsze zwracamy co najmniej 1 token dla niepustego tekstu.
        return max(1, estimated_tokens)

    def count_chat(self, messages: Sequence[LLMMessage]) -> int:
        """Szacuje liczbę tokenów w całej sekwencji wiadomości.

        Args:
        ----
            messages: Sekwencja obiektów `LLMMessage`.

        Returns:
        -------
            Oszacowana, całkowita liczba tokenów dla całej konwersacji.

        """
        if not messages:
            return 0
        # Sumujemy tokeny dla każdej wiadomości, użyjemy generatora.
        return sum(self.count_tokens(m.content) for m in messages)
