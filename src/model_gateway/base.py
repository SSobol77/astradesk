# src/model_gateway/base.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Author: Siergej Sobolewski
#
# Cel modułu
# ----------
# Podstawowe typy, kontrakty i narzędzia dla warstwy "Model Gateway":
#  - ujednolicone modele wiadomości (LLMMessage) i parametrów (ChatParams),
#  - interfejs providera LLM z trybem pełnym i streamingowym,
#  - wyjątki domenowe (konfiguracja, limity, time-out, serwer),
#  - funkcje pomocnicze do mapowania wiadomości na formaty API (OpenAI/Anthropic),
#  - opcjonalny interfejs tokenizatora do policzenia użycia (usage).
#
# Dzięki temu konkretni providerzy (OpenAI, Bedrock, vLLM, itp.) mogą zaimplementować
# tę samą sygnaturę publiczną, a reszta systemu pozostaje stabilna.

from __future__ import annotations

import httpx
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, Sequence, Tuple

from dataclasses import dataclass, field
from enum import Enum



# ---------------------------------------------------------------------------
# Wyjątki specyficzne dla warstwy Model Gateway
# ---------------------------------------------------------------------------

# ===========================
# ModelGatewayError
# ===========================
@dataclass
class ModelGatewayError(RuntimeError):
    """
    Ogólny błąd warstwy Model Gateway, niosący pełny kontekst diagnostyczny.

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
    provider: Optional[str] = None
    status_code: Optional[int] = None
    request_id: Optional[str] = None
    retry_after: Optional[float] = None
    details: Any = None
    raw: Any = None

    def __str__(self) -> str:
        # Składamy krótki, ale bogaty w kontekst komunikat do logów/tracingu.
        parts = [self.message or self.__class__.__name__]
        if self.provider:
            parts.append(f"[provider={self.provider}]")
        if self.status_code is not None:
            parts.append(f"[status={self.status_code}]")
        if self.request_id:
            parts.append(f"[request_id={self.request_id}]")
        if self.retry_after is not None:
            parts.append(f"[retry_after={self.retry_after}s]")
        return " ".join(parts)

    # ---- Fabryki ułatwiające mapowanie błędów HTTP/SDK na wyjątki domenowe ----

    @classmethod
    def from_httpx(
        cls,
        exc: "httpx.HTTPError",
        *,
        provider: str,
        fallback_message: str = "Provider HTTP error",
        request_id_header: str = "x-request-id",
    ) -> "ModelGatewayError":
        """
        Mapuje httpx.HTTPError/HTTPStatusError → ModelGatewayError z kontekstem.
        (Lokalny import httpx, by nie wymuszać zależności poza providerami.)
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
            # spróbuj JSON → tekst
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
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[float] = None,
        details: Any = None,
        raw: Any = None,
    ) -> "ModelGatewayError":
        """
        Ogólna fabryka gdy masz inny typ odpowiedzi (np. boto3 Bedrock Runtime,
        klient SDK providera, albo response bez httpx).
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
# ProviderTimeout
# ===========================
@dataclass
class ProviderTimeout(ModelGatewayError):
    """
    Zapytanie do providera przekroczyło dopuszczalny czas (timeout).

    Pola (uzupełniają bazowe pola ModelGatewayError):
      - timeout:   skonfigurowany limit czasu w sekundach (np. 30.0),
      - elapsed:   ile realnie upłynęło czasu zanim nastąpił timeout,
      - phase:     faza, w której zaszło przekroczenie ("connect", "read", "write", "overall"),
      - endpoint:  adres/URL końcówki API (przydatne do korelacji),
      - attempts:  ile razy ponawiano żądanie (retry), jeśli stosujesz backoff.
    """
    timeout: Optional[float] = None
    elapsed: Optional[float] = None
    phase: Optional[str] = None       # "connect" | "read" | "write" | "overall" | None
    endpoint: Optional[str] = None
    attempts: Optional[int] = None

    def __str__(self) -> str:
        # Zwięzły, diagnostyczny komunikat do logów/observability.
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
        timeout: Optional[float] = None,
        endpoint: Optional[str] = None,
        phase: Optional[str] = None,
        attempts: Optional[int] = None,
        elapsed: Optional[float] = None,
        request_id: Optional[str] = None,
        details: Any = None,
        raw: Any = None,
        message: str = "Provider HTTP timeout",
    ) -> "ProviderTimeout":
        """
        Utwórz wyjątek dla timeoutów z bibliotek HTTP (np. httpx.ReadTimeout).

        Użycie:
            except httpx.ReadTimeout as e:
                raise ProviderTimeout.from_httpx_timeout(
                    provider="openai",
                    timeout=30.0,
                    endpoint=OPENAI_URL,
                    phase="read",
                    attempts=ctx.retries,
                    raw=e,
                )
        """
        return cls(
            message=message,
            provider=provider,
            status_code=None,    # timeout zwykle bez kodu HTTP
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
        timeout: Optional[float],
        endpoint: Optional[str] = None,
        attempts: Optional[int] = None,
        elapsed: Optional[float] = None,
        message: str = "Provider asyncio timeout",
        raw: Any = None,
    ) -> "ProviderTimeout":
        """
        Utwórz wyjątek na bazie `asyncio.TimeoutError` (gdy stosujesz `asyncio.wait_for`).
        """
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
        started_at_seconds: Optional[float] = None,
        endpoint: Optional[str] = None,
        attempts: Optional[int] = None,
        message: str = "Provider deadline exceeded",
    ) -> "ProviderTimeout":
        """
        Gdy masz własny „deadline” (np. termin SLA na całą operację) i sam sprawdzasz czas.
        """
        elapsed = None
        try:
            if started_at_seconds is not None:
                elapsed = max(0.0, time.time() - started_at_seconds)
        except Exception:
            pass

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
# ProviderOverloaded
# ===========================
@dataclass
class ProviderOverloaded(ModelGatewayError):
    """
    Provider przeciążony / throttling (np. HTTP 429, throttling SDK).

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
    limit: Optional[int] = None
    remaining: Optional[int] = None
    window: Optional[str] = None
    reset_at: Optional[float] = None        # epoch seconds (UTC)
    reset_after: Optional[float] = None      # sekundy (relative)
    scope: Optional[str] = None              # np. "requests", "tokens"
    bucket: Optional[str] = None             # np. "org_xxx", "project_yyy"
    region: Optional[str] = None
    reason: Optional[str] = None             # np. "rate_limited" | "quota_exhausted"

    def __str__(self) -> str:
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
            iso = datetime.fromtimestamp(self.reset_at, tz=timezone.utc).isoformat()
            parts.append(f"[reset_at={iso}]")
        if self.retry_after is not None:
            parts.append(f"[retry_after={self.retry_after}s]")
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
    def _parse_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _parse_epoch(value: Any) -> Optional[float]:
        """
        Próbujemy zinterpretować wartość jako epoch sekundy. Jeśli jest to
        ISO8601, nie parsujemy tutaj (zachowujemy prostotę) – preferujemy
        nagłówki typu "reset-after". W razie potrzeby można dodać parser ISO.
        """
        try:
            v = float(value)
            if v > 10_000_000:  # heurystyka: to raczej ms
                return v / 1000.0
            return v
        except Exception:
            return None

    @classmethod
    def _parse_rate_limit_headers(cls, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Normalizuje znane nagłówki limitowania do wspólnych pól.

        Obsługiwane (best-effort):
          - IETF draft: RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset
          - OpenAI: x-ratelimit-limit-requests, x-ratelimit-remaining-requests,
                    x-ratelimit-reset-requests, x-request-id
                    (oraz odpowiedniki *-tokens)
          - Anthropic: anthropic-ratelimit-requests-remaining, ...-reset, itd.
          - Ogólne: Retry-After (sekundy) — priorytetowo traktowane
        """
        # Ujednolicamy klucze nagłówków na lower-case dla łatwiejszego dopasowania
        h = {k.lower(): v for k, v in (headers or {}).items()}

        out: Dict[str, Any] = {}

        # 1) Retry-After: najprostsze i najwyższy priorytet (sekundy lub data HTTP-date)
        ra = h.get("retry-after")
        if ra:
            # Może być liczba sekund albo data HTTP-date. Spróbujemy liczbowo:
            ra_val = cls._parse_float(ra)
            if ra_val is None:
                # Minimalny parse HTTP-date → konwertuj na epoch i odejmij now
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(ra)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    out["retry_after"] = max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())
                except Exception:
                    out["retry_after"] = None
            else:
                out["retry_after"] = max(0.0, ra_val)

        # 2) IETF draft "RateLimit-*"
        if "ratelimit-remaining" in h:
            out["remaining"] = cls._parse_int(h.get("ratelimit-remaining"))
        if "ratelimit-limit" in h:
            out["limit"] = cls._parse_int(h.get("ratelimit-limit"))
        # IETF draft dopuszcza składnię: "limit;w=60"
        rl_limit_raw = h.get("ratelimit-limit")
        if rl_limit_raw and ";" in rl_limit_raw:
            try:
                # przykłady: "100;w=60", "100; window=60"
                parts = [p.strip() for p in rl_limit_raw.split(";")]
                for p in parts[1:]:
                    if p.startswith("w="):
                        w = p.split("=", 1)[1]
                        # zapisz okno w sekundach jako string "60s"
                        out["window"] = f"{int(w)}s"
                        break
                    if "window=" in p:
                        w = p.split("=", 1)[1]
                        out["window"] = f"{int(w)}s"
                        break
            except Exception:
                pass

        if "ratelimit-reset" in h:
            # bywa w sekundach względnych lub epoch — traktuj jako sekundy względne
            out["reset_after"] = cls._parse_float(h.get("ratelimit-reset"))

        # 3) OpenAI style (requests/tokens; wybieramy „ostrzejszy” sygnał)
        # requests
        rl_rem_req = cls._parse_int(h.get("x-ratelimit-remaining-requests"))
        rl_lim_req = cls._parse_int(h.get("x-ratelimit-limit-requests"))
        rl_rst_req = cls._parse_float(h.get("x-ratelimit-reset-requests"))  # zwykle sekundy względne
        # tokens
        rl_rem_tok = cls._parse_int(h.get("x-ratelimit-remaining-tokens"))
        rl_lim_tok = cls._parse_int(h.get("x-ratelimit-limit-tokens"))
        rl_rst_tok = cls._parse_float(h.get("x-ratelimit-reset-tokens"))

        # wybór ścieżki (scope= "requests" vs "tokens") – preferuj ostrzejsze ograniczenie (mniej remaining)
        if rl_rem_req is not None or rl_rem_tok is not None:
            if rl_rem_tok is not None and (rl_rem_req is None or rl_rem_tok < rl_rem_req):
                out.update({
                    "remaining": rl_rem_tok,
                    "limit": rl_lim_tok,
                    "reset_after": rl_rst_tok,
                    "scope": "tokens",
                })
            else:
                out.update({
                    "remaining": rl_rem_req,
                    "limit": rl_lim_req,
                    "reset_after": rl_rst_req,
                    "scope": "requests",
                })

        # 4) Anthropic style (przykładowe; best-effort)
        ar_rem = cls._parse_int(h.get("anthropic-ratelimit-requests-remaining"))
        ar_lim = cls._parse_int(h.get("anthropic-ratelimit-requests-limit"))
        ar_rst = cls._parse_float(h.get("anthropic-ratelimit-requests-reset"))
        if ar_rem is not None:
            out.update({
                "remaining": ar_rem,
                "limit": ar_lim if ar_lim is not None else out.get("limit"),
                "reset_after": ar_rst if ar_rst is not None else out.get("reset_after"),
                "scope": out.get("scope") or "requests",
            })
        # tokens wariant
        ar_rem_tok = cls._parse_int(h.get("anthropic-ratelimit-tokens-remaining"))
        ar_lim_tok = cls._parse_int(h.get("anthropic-ratelimit-tokens-limit"))
        ar_rst_tok = cls._parse_float(h.get("anthropic-ratelimit-tokens-reset"))
        if ar_rem_tok is not None:
            # wybierz ostrzejszy
            cur = out.get("remaining")
            if cur is None or (ar_rem_tok < cur):
                out.update({
                    "remaining": ar_rem_tok,
                    "limit": ar_lim_tok if ar_lim_tok is not None else out.get("limit"),
                    "reset_after": ar_rst_tok if ar_rst_tok is not None else out.get("reset_after"),
                    "scope": "tokens",
                })

        # 5) Identyfikatory żądania (różni vendorzy)
        out["request_id"] = h.get("x-request-id") or h.get("request-id") or h.get("x-amzn-requestid") or h.get("x-amzn-request-id")

        return out

    @classmethod
    def from_httpx_429(
        cls,
        exc: "httpx.HTTPStatusError",
        *,
        provider: str,
        message: str = "Rate limited / overloaded",
        reason: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> "ProviderOverloaded":
        """
        Fabryka do mapowania httpx.HTTPStatusError 429 → ProviderOverloaded.
        Pobiera standardowe „RateLimit-*” i vendorowe nagłówki, ustawia retry_after/reset.
        """
        import httpx  # lazy import
        assert isinstance(exc, httpx.HTTPStatusError), "from_httpx_429 expects HTTPStatusError"

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
        """
        Heurystyka: True jeśli wygląda na "quota exhausted" (twardy limit),
        czyli 'remaining' == 0 oraz reset_after/reset_at są daleko w czasie,
        lub provider podał reason, które wskazuje na kwotę (nie burst).
        """
        if self.reason and "quota" in self.reason.lower():
            return True
        if self.remaining == 0:
            # jeśli brak informacji o reset, traktuj jako hard (lepszy dłuższy backoff)
            return True
        return False

    def suggested_sleep(self, *, attempts: int = 0, base: float = 1.0, cap: float = 60.0, jitter: bool = True) -> float:
        """
        Zwraca rekomendowany czas uśpienia (sekundy) przed ponowną próbą.

        Priorytety:
          1) Jeśli istnieje 'retry_after' → zwróć je (trust provider).
          2) W przeciwnym razie, jeśli jest 'reset_after'/'reset_at' → policz do resetu.
          3) W przeciwnym razie exponential backoff: min(cap, base * 2**attempts) [+ jitter].

        :param attempts: numer próby (0 dla pierwszej), determinuje backoff
        :param base: baza backoffu
        :param cap: maksymalny czas snu
        :param jitter: losowy jitter, aby uniknąć „thundering herd”
        """
        # 1) Retry-After od providera ma najwyższy priorytet
        if self.retry_after is not None:
            return max(0.0, float(self.retry_after))

        # 2) Reset (relatywny lub absolutny)
        now = time.time()
        if self.reset_after is not None:
            return max(0.0, float(self.reset_after))
        if self.reset_at is not None:
            return max(0.0, float(self.reset_at - now))

        # 3) Exponential backoff
        delay = min(float(cap), float(base) * (2.0 ** max(0, attempts)))
        if jitter:
            try:
                import random
                # „full jitter” (AWS best-practice): losuj z [0, delay]
                delay = random.uniform(0.0, delay)
            except Exception:
                pass
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
    """
    Błąd po stronie serwera providera (5xx lub ekwiwalent SDK).

    Po co osobna klasa?
      - Rozróżnia awarie *u providera* (5xx) od błędów klienta/konfiguracji,
      - Niesie kontekst do decyzji o retry/backoff (retryable?, retry-after, rodzina statusu),
      - Ułatwia spójne logowanie/alertowanie (status, request_id, szczegóły odpowiedzi).

    Dodatkowe pola:
      status_family : rodzina statusu HTTP (np. 500, 502, 503, 504) – ułatwia strategię retry,
      endpoint      : adres/operacja, na którą zgłaszaliśmy żądanie,
      retryable     : heurystyka, czy warto spróbować ponownie (domyślnie True dla 502/503/504),
      upstream      : (opcjonalnie) nazwa usługi/regionu po stronie providera, jeśli raportuje,
      reason        : krótki powód/etykieta (np. "bad_gateway", "unavailable", "timeout").
    """
    status_family: Optional[int] = None
    endpoint: Optional[str] = None
    retryable: Optional[bool] = None
    upstream: Optional[str] = None
    reason: Optional[str] = None

    def __str__(self) -> str:
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
            parts.append(f"[retry_after={self.retry_after}s]")
        if self.retryable is not None:
            parts.append(f"[retryable={self.retryable}]")
        if self.upstream:
            parts.append(f"[upstream={self.upstream}]")
        if self.reason:
            parts.append(f"[reason={self.reason}]")
        return " ".join(parts)

    # -------- Fabryki / mapowanie 5xx --------

    @staticmethod
    def _parse_retry_after(headers: Dict[str, str]) -> Optional[float]:
        """
        Parser 'Retry-After' (sekundy lub HTTP-date). Zwraca sekundy (float) albo None.
        """
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
            # HTTP-date → konwersja na sekundy do przyszłości
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(ra)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())
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
    def from_httpx_5xx(
        cls,
        exc: "httpx.HTTPStatusError",
        *,
        provider: str,
        endpoint: Optional[str] = None,
        message: str = "Provider 5xx server error",
        request_id_header: str = "x-request-id",
        reason: Optional[str] = None,
    ) -> "ProviderServerError":
        """
        Mapuje httpx.HTTPStatusError (5xx) → ProviderServerError z pełnym kontekstem.
        Ustawia: status_code, status_family, request_id, retry_after, heurystykę retryable.
        """
        import httpx  # lazy import
        assert isinstance(exc, httpx.HTTPStatusError), "from_httpx_5xx expects HTTPStatusError"

        resp = exc.response
        status = resp.status_code
        headers = dict(resp.headers or {})
        req_id = (
            headers.get(request_id_header)
            or headers.get("x-amzn-requestid")
            or headers.get("x-amzn-request-id")
        )
        retry_after = cls._parse_retry_after(headers)
        family = (status // 100) * 100 if status is not None else None
        # heurystyka retry: 502/503/504 zwykle retryable, 500 — raczej nie
        retryable = True if status in (502, 503, 504) else (False if status == 500 else None)

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
        status_code: Optional[int],
        message: str,
        endpoint: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[float] = None,
        details: Any = None,
        raw: Any = None,
        retryable: Optional[bool] = None,
        reason: Optional[str] = None,
        upstream: Optional[str] = None,
    ) -> "ProviderServerError":
        """
        Fabryka dla innych źródeł (boto3 Bedrock, SDK vendora, itp.).
        """
        family = (status_code // 100) * 100 if status_code is not None else None
        if retryable is None and status_code is not None:
            retryable = True if status_code in (502, 503, 504) else (False if status_code == 500 else None)
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
        """
        Zwraca zalecany czas uśpienia (sekundy) przed retry.
        1) użyj `retry_after` gdy provider go podał,
        2) w przeciwnym razie exponential backoff (full jitter).
        """
        if self.retry_after is not None:
            return max(0.0, float(self.retry_after))
        delay = min(float(cap), float(base) * (2.0 ** max(0, attempts)))
        if jitter:
            try:
                import random
                delay = random.uniform(0.0, delay)
            except Exception:
                pass
        return delay

    def should_retry(self) -> bool:
        """
        Czy w ogóle próbować ponownie?
          - True dla 502/503/504,
          - False dla 500 (zazwyczaj błąd trwały),
          - unknown 5xx → True (ostrożnie, pojedynczy retry).
        """
        if self.retryable is not None:
            return bool(self.retryable)
        if self.status_code in (502, 503, 504):
            return True
        if self.status_code == 500:
            return False
        return True


# ===========================
# TokenLimitExceeded (limity)
# ===========================
@dataclass
class TokenLimitExceeded(ModelGatewayError):
    """
    Przekroczony limit tokenów modelu (kontekst / output / polityka providera).

    Przykłady przyczyn:
      - prompt_tokens + max_tokens > context_window modelu,
      - provider odmówił z powodu limitów (np. "context_length_exceeded"),
      - zbyt długi jeden dokument / message.

    Dodatkowe pola diagnostyczne:
      model            : identyfikator modelu (np. "gpt-4o", "claude-3-sonnet"),
      context_window   : maksymalny kontekst (liczba tokenów),
      prompt_tokens    : tokeny wejścia (liczone lub zwrócone przez providera),
      completion_limit : maksymalny dozwolony output (jeśli provider raportuje),
      requested_output : żądane `max_tokens` w parametrze wywołania,
      overflow         : o ile przekroczono limit (jeśli policzalne),
      strategy         : rekomendowana strategia redukcji (np. "truncate_messages", "reduce_rag", "summarize"),
      tips             : krótkie wskazówki (np. co skrócić).

    Metody:
      - suggest_truncation(): proponuje, ile tokenów trzeba ściąć z promptu,
      - from_provider_payload(): fabryka z mapowaniem typowych odpowiedzi providerów.
    """
    model: Optional[str] = None
    context_window: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_limit: Optional[int] = None
    requested_output: Optional[int] = None
    overflow: Optional[int] = None
    strategy: Optional[str] = None
    tips: Optional[str] = None

    def __str__(self) -> str:
        parts = [self.message or "Token limit exceeded"]
        if self.provider:
            parts.append(f"[provider={self.provider}]")
        if self.model:
            parts.append(f"[model={self.model}]")
        if self.context_window is not None:
            parts.append(f"[context_window={self.context_window}]")
        if self.prompt_tokens is not None:
            parts.append(f"[prompt_tokens={self.prompt_tokens}]")
        if self.requested_output is not None:
            parts.append(f"[requested_output={self.requested_output}]")
        if self.overflow is not None:
            parts.append(f"[overflow={self.overflow}]")
        if self.strategy:
            parts.append(f"[strategy={self.strategy}]")
        return " ".join(parts)

    # --------- Logika pomocnicza / rekomendacje ---------

    def suggest_truncation(self) -> Optional[int]:
        """
        Zwraca sugerowaną liczbę tokenów do „ucięcia” z promptu,
        aby zmieścić się w `context_window`, jeśli znamy wszystkie składniki.
        """
        if self.context_window is None:
            return None
        pt = int(self.prompt_tokens or 0)
        ro = int(self.requested_output or 0)
        # ile tokenów zostaje na prompt, jeśli chcemy zostawić requested_output
        max_prompt = self.context_window - ro if ro > 0 else self.context_window
        return max(0, pt - max_prompt)

    def recommend_strategy(self) -> Tuple[str, str]:
        """
        Zwraca (strategy, tips) – zalecenie jak zejść z limitu.
        """
        # Priorytety: 1) skróć RAG/dokumenty, 2) skróć historię chatu, 3) zmniejsz max_tokens
        trunc = self.suggest_truncation()
        if trunc and trunc > 0:
            return (
                "truncate_messages",
                f"Zredukuj prompt o ~{trunc} tokenów (usuń starsze wiadomości, skróć RAG lub streść dokumenty).",
            )
        if self.requested_output and self.context_window is not None and self.prompt_tokens is not None:
            # Może wystarczy obniżyć 'max_tokens'
            pt = int(self.prompt_tokens)
            room = max(0, int(self.context_window) - pt)
            if room > 0 and self.requested_output > room:
                return ("reduce_max_tokens", f"Zmniejsz max_tokens z {self.requested_output} do ≤ {room}.")
        return ("summarize", "Skróć wejście (np. streszczenie długich fragmentów RAG) i usuń szum.")

    # --------- Fabryki / mapowanie z odpowiedzi providerów ---------

    @classmethod
    def from_provider_payload(
        cls,
        *,
        provider: str,
        message: str = "Token/context limit exceeded",
        model: Optional[str] = None,
        context_window: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        requested_output: Optional[int] = None,
        completion_limit: Optional[int] = None,
        details: Any = None,
        raw: Any = None,
        request_id: Optional[str] = None,
    ) -> "TokenLimitExceeded":
        """
        Ogólna fabryka, gdy sam liczysz tokeny lub parsujesz błąd z SDK.
        Ustal również `overflow`, jeśli dane pozwalają.
        """
        overflow = None
        try:
            if context_window is not None:
                pt = int(prompt_tokens or 0)
                ro = int(requested_output or 0)
                overflow = max(0, (pt + ro) - int(context_window))
        except Exception:
            overflow = None

        # sugerowana strategia/tips:
        inst = cls(
            message=message,
            provider=provider,
            model=model,
            context_window=context_window,
            prompt_tokens=prompt_tokens,
            requested_output=requested_output,
            completion_limit=completion_limit,
            overflow=overflow,
            details=details,
            raw=raw,
            request_id=request_id,
        )
        strat, tip = inst.recommend_strategy()
        inst.strategy = strat
        inst.tips = tip
        return inst

    @classmethod
    def from_httpx_response(
        cls,
        resp: "httpx.Response",
        *,
        provider: str,
        message: str = "Token/context limit exceeded",
        model: Optional[str] = None,
        request_id_header: str = "x-request-id",
    ) -> "TokenLimitExceeded":
        """
        Próbuje zbudować wyjątek na podstawie odpowiedzi HTTP providera,
        który zwrócił informację o przekroczeniu limitu (status bywa 400/413/422).
        Best-effort: postara się wyciągnąć liczby z JSON-a.
        """
        import httpx  # lazy import
        assert isinstance(resp, httpx.Response)
        details: Any = None
        try:
            details = resp.json()
        except Exception:
            try:
                details = resp.text
            except Exception:
                details = None

        # Spróbuj zmapować typowe nazwy pól, jeśli provider je raportuje:
        ctx = None
        pt = None
        req_out = None
        comp_lim = None
        try:
            if isinstance(details, dict):
                ctx = details.get("context_window") or details.get("max_context") or details.get("maximum_tokens")
                pt = details.get("prompt_tokens") or details.get("input_tokens")
                req_out = details.get("requested_output") or details.get("max_tokens")
                comp_lim = details.get("completion_limit") or details.get("output_tokens_limit")
        except Exception:
            pass

        return cls.from_provider_payload(
            provider=provider,
            message=message,
            model=model,
            context_window=ctx if isinstance(ctx, int) else None,
            prompt_tokens=pt if isinstance(pt, int) else None,
            requested_output=req_out if isinstance(req_out, int) else None,
            completion_limit=comp_lim if isinstance(comp_lim, int) else None,
            details=details,
            raw=resp,
            request_id=resp.headers.get(request_id_header) or resp.headers.get("x-amzn-requestid"),
        )


# ---------------------------------------------------------------------------
# Rola komunikatu + model wiadomości
# ---------------------------------------------------------------------------
class Role(str, Enum):
    """
    Ustandaryzowane role w rozmowie:
      - system:     instrukcje wysokiego poziomu (policy/guardrails),
      - user:       pytanie / polecenie użytkownika,
      - assistant:  odpowiedź modelu (może zawierać narzędzia),
      - tool:       odpowiedź narzędzia (jeśli provider wspiera „function/tool calls”).
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class LLMMessage:
    """
    Reprezentuje pojedynczą wiadomość w rozmowie.

    Pola:
      role:    rola nadawcy (system/user/assistant/tool),
      content: treść (czysty tekst; dla „tool” zwykle JSON -> str).

    Uwaga:
      - modelowane minimalistycznie; konkretni providerzy mogą rozszerzać
        ten format (np. części multimodalne), ale base API trzyma tekst.
    """
    role: str
    content: str

    def as_dict(self) -> Dict[str, str]:
        """Lekka reprezentacja słownikowa (przydatna do logów/serializacji)."""
        return {"role": self.role, "content": self.content}

    @staticmethod
    def system(text: str) -> "LLMMessage":
        return LLMMessage(role=Role.SYSTEM.value, content=text)

    @staticmethod
    def user(text: str) -> "LLMMessage":
        return LLMMessage(role=Role.USER.value, content=text)

    @staticmethod
    def assistant(text: str) -> "LLMMessage":
        return LLMMessage(role=Role.ASSISTANT.value, content=text)

    @staticmethod
    def tool(text: str) -> "LLMMessage":
        return LLMMessage(role=Role.TOOL.value, content=text)


# ---------------------------------------------------------------------------
# Parametry chatu + usage + chunk do streamingu
# ---------------------------------------------------------------------------
def _clamp(v: float, lo: float, hi: float) -> float:
    return hi if v > hi else lo if v < lo else v


@dataclass(slots=True)
class ChatParams:
    """
    Parametry generacji dla modeli czatowych.

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
    stop: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "ChatParams":
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
    """
    Statystyki wykorzystania tokenów (jeśli provider udostępnia).
      - prompt_tokens: tokeny wejścia,
      - completion_tokens: tokeny wyjścia,
      - total_tokens: suma.
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(slots=True)
class ChatChunk:
    """
    Pojedynczy fragment strumienia odpowiedzi.
      - delta: kolejna porcja tekstu,
      - finish_reason: opcjonalny sygnał końca (np. "stop", "length"),
      - usage: narastające usage (jeśli provider raportuje w trakcie).
    """
    delta: str
    finish_reason: Optional[str] = None
    usage: Optional[Usage] = None


# ---------------------------------------------------------------------------
# Interfejs tokenizatora (opcjonalny)
# ---------------------------------------------------------------------------
class Tokenizer(Protocol):
    """
    Opcjonalny kontrakt tokenizatora – provider może go użyć do raportowania usage,
    albo do wczesnego sprawdzenia limitów tokenów (preflight).
    """
    def count_tokens(self, text: str) -> int: ...
    def count_chat(self, messages: Sequence[LLMMessage]) -> int: ...


# ---------------------------------------------------------------------------
# Kontrakt providera LLM
# ---------------------------------------------------------------------------
class LLMProvider(Protocol):
    """
    Kontrakt, który muszą spełnić konkretni providerzy (OpenAI/Bedrock/vLLM/…).
    Wymaga dwóch metod:
      - chat():    pełna odpowiedź jako string (+ ew. usage zwracany „out-of-band”),
      - stream():  fragmenty odpowiedzi jako asynchroniczny iterator ChatChunk.

    Zalecenia implementacyjne:
      - obsługuj ProviderTimeout / ProviderOverloaded / ProviderServerError
        mapując kody HTTP/SDK na wyjątki warstwy Model Gateway,
      - jeśli znasz usage → udostępnij przez parametry/metody zwrotne (np. pola extra).
    """

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: Optional[ChatParams] = None,
        tokenizer: Optional[Tokenizer] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """
        Zwraca pełną odpowiedź jako string.

        :param messages: historia rozmowy (system→user→assistant→…),
        :param params: parametry generacji (clampowane w normalized()),
        :param tokenizer: opcjonalny tokenizator do preflight/usage,
        :param request_id: identyfikator żądania (do tracingu/logów).
        :raises ProviderConfigError, ProviderTimeout, ProviderOverloaded,
                ProviderServerError, TokenLimitExceeded
        """
        ...

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: Optional[ChatParams] = None,
        tokenizer: Optional[Tokenizer] = None,
        request_id: Optional[str] = None,
    ) -> AsyncIterator[ChatChunk]:
        """
        Zwraca asynchroniczny strumień fragmentów odpowiedzi (ChatChunk).
        Implementacje providerów MUSZĄ dostarczyć ciało metody.
        """
        ...


# ---------------------------------------------------------------------------
# Adaptery formatów wiadomości (ułatwiają pisanie providerów)
# ---------------------------------------------------------------------------
def to_openai_messages(messages: Sequence[LLMMessage]) -> List[Dict[str, str]]:
    """
    Mapuje LLMMessage → format OpenAI Chat API:
      {"role": "<role>", "content": "<content>"}
    """
    out: List[Dict[str, str]] = []
    for m in messages:
        role = m.role
        if role == Role.TOOL.value:
            # OpenAI nie ma roli "tool" w standardowej ścieżce treści tekstowych;
            # zwykle łączy się to jako "assistant" z function_call / tool_call.
            role = Role.ASSISTANT.value
        out.append({"role": role, "content": m.content})
    return out


def to_anthropic_messages(messages: Sequence[LLMMessage]) -> List[Dict[str, str]]:
    """
    Mapuje LLMMessage → przybliżony format Anthropic Messages API.
    Uwaga: rzeczywisty format może wymagać listy „content blocks” – ten adapter
    jest minimalistyczny i nadaje się do prostego tekstu.
    """
    out: List[Dict[str, str]] = []
    for m in messages:
        role = "user" if m.role in (Role.USER.value, Role.SYSTEM.value) else "assistant"
        out.append({"role": role, "content": m.content})
    return out


# ---------------------------------------------------------------------------
# Walidacja historii (przydatna w providerach)
# ---------------------------------------------------------------------------

def validate_conversation(messages: Sequence[LLMMessage]) -> None:
    """
    Prosta walidacja spójności historii:
      - brak pustych treści,
      - pierwszy komunikat zwykle 'system' lub 'user',
      - role w dozwolonym zbiorze.

    W razie potrzeby dopisz bardziej zaawansowane reguły (np. naprzemienność U-A).
    """
    if not messages:
        raise ValueError("Conversation must contain at least one message.")
    allowed = {r.value for r in Role}
    if messages[0].role not in (Role.SYSTEM.value, Role.USER.value):
        raise ValueError("Conversation should start with a 'system' or 'user' message.")
    for m in messages:
        if not m.content:
            raise ValueError("Message content must not be empty.")
        if m.role not in allowed:
            raise ValueError(f"Unsupported role: {m.role!r}.")


# ---------------------------------------------------------------------------
# Domyślny, „pusty” tokenizator (noop), jeżeli provider nie posiada własnego
# ---------------------------------------------------------------------------

class NoopTokenizer:
    """Minimalny tokenizator: liczy tokeny z grubsza jako słowa (heurystyka)."""

    def count_tokens(self, text: str) -> int:
        # Bardzo łagodna heurystyka: ~1 token ≈ 0.75 słowa; zaokrąglamy w górę.
        if not text:
            return 0
        words = max(1, len(text.split()))
        return int((words / 0.75) + 0.999)

    def count_chat(self, messages: Sequence[LLMMessage]) -> int:
        return sum(self.count_tokens(m.content) for m in messages)
