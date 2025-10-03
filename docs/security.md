# Bezpieczeństwo - AstraDesk

Kompletny przewodnik bezpieczeństwa dla architektury, wdrożenia i procesu wytwórczego systemu **AstraDesk**. Dokument obejmuje: model zagrożeń, kontrolę dostępu, ochronę danych, bezpieczeństwo środowisk (Kubernetes + mesh), łańcuch dostaw oprogramowania (SBOM), logowanie/audyt, reagowanie na incydenty oraz zgodność.

<br>

---

## 1) Model zagrożeń (Threat Model) - STRIDE (skrót)

| Kategoria | Ryzyko | Przykład | Kontrola w AstraDesk |
|---|---|---|---|
| **S**poofing | Podszycie pod użytkownika/usługę | Fałszywy bearer token | OIDC+JWKS, weryfikacja `iss/aud/exp/nbf`, mTLS w mesh |
| **T**ampering | Modyfikacja żądań/danych | In‑transit MITM, zmiana payloadu | TLS/mTLS, podpis JWT, walidacja schematów |
| **R**epudiation | Wyparcie się akcji | „To nie ja” | Audyt niezmienny (S3 WORM), NATS->Auditor, time‑stamps |
| **I**nformation Disclosure | Ujawnienie danych | PII w logach | Maskowanie logów, RBAC, szyfrowanie at‑rest/in‑transit |
| **D**enial of Service | Wyczerpanie zasobów | Lawina zapytań do LLM | Rate limit, backoff, HPA, circuit breaker |
| **E**levation of Privilege | Eskalacja uprawnień | Zwykły user wykonuje `restart_service` | RBAC/ABAC w toolach, least privilege, review polityk |

> Pełny diagram DFD patrz `architecture.md`.

<br>

---

## 2) Uwierzytelnianie (AuthN) - OIDC/JWT

- **Źródło prawdy**: zewnętrzny IdP (np. Keycloak/Azure AD/Okta).  
- **Weryfikacja**: JWKS (`kid`), `iss`, `aud`, `exp`, `nbf`; odrzucaj `alg=none`.  
- **Clock‑skew**: dopuszczalne ±60s.  
- **Nagłówek**: `Authorization: Bearer <JWT>`; brak -> `401`.

### Przykład (FastAPI) - weryfikacja JWT (skrót)
```python
claims = await oidc_cfg.verify(token)  # sprawdza podpis + iss/aud/exp/nbf
sub = claims.get("sub")
roles = claims.get("roles") or claims.get("groups") or claims.get("realm_access", {}).get("roles", [])
```

<br>

---

## 3) Autoryzacja (AuthZ) - RBAC/ABAC

- **RBAC w toolach**: każda funkcja narzędzia sprawdza role z `claims` (minimalny zakres).  
- **ABAC** (opcjonalnie): polityki oparte o atrybuty (`department`, `owner`, `env`).  
- **Zasada** *least privilege*: nadawaj tylko niezbędne role (`sre`, `it.support`, ...).

### Przykład - egzekwowanie roli w narzędziu
```python
def _has_role(claims: dict, role: str) -> bool:
    roles = (claims or {}).get("roles") or (claims or {}).get("groups") or []
    realm = (claims or {}).get("realm_access", {})
    if isinstance(realm, dict):
        roles = roles + (realm.get("roles") or [])
    return role in {str(r) for r in roles}

async def restart_service(service: str, *, claims: dict | None = None) -> str:
    if not _has_role(claims or {}, "sre"):
        raise AuthorizationError("Odmowa - brak roli 'sre'.")
    # ...
```

<br>

---

## 4) mTLS i sieć (Service Mesh + NetworkPolicy)

- **Mesh**: Istio/Linkerd z **STRICT mTLS** między podami.  
- **TLS do zewnętrznych**: wymuś TLS 1.2+ i weryfikację certyfikatów.  
- **K8s NetworkPolicy**: ogranicz ruch egress/ingress do niezbędnych namespace/podów.

### PeerAuthentication (STRICT)
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: astradesk-peer-auth
  namespace: astradesk
spec:
  mtls:
    mode: STRICT
```

### NetworkPolicy - przykład (pods -> Postgres/Redis/NATS)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-core-egress
  namespace: astradesk
spec:
  podSelector: {}
  policyTypes: [ Egress ]
  egress:
    - to:
        - namespaceSelector: { matchLabels: { name: "data" } }
          podSelector: { matchLabels: { app: "postgres" } }
      ports: [ { port: 5432, protocol: TCP } ]
    - to:
        - namespaceSelector: { matchLabels: { name: "data" } }
          podSelector: { matchLabels: { app: "redis" } }
      ports: [ { port: 6379, protocol: TCP } ]
    - to:
        - namespaceSelector: { matchLabels: { name: "messaging" } }
          podSelector: { matchLabels: { app: "nats" } }
      ports: [ { port: 4222, protocol: TCP } ]
```

<br>

---

## 5) Zarządzanie sekretami i kluczami

- **Źródła**: K8s Secrets (szyfrowane w etcd), **AWS Secrets Manager**/**HashiCorp Vault**.  
- **KMS**: AWS KMS dla S3/Secrets/Elasticsearch snapshot repo.  
- **Rotacja**: cykliczna rotacja kluczy API/LLM, automatyczne odświeżanie podów.  
- **Nigdy** nie commituj sekretów do repo; ogranicz echo w logach.

### Przykład - Secret + envFrom
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: astradesk-secrets
type: Opaque
stringData:
  OPENAI_API_KEY: "****"
  DATABASE_URL: "postgresql://user:pass@pg:5432/astradesk"
---
apiVersion: apps/v1
kind: Deployment
# ...
spec:
  template:
    spec:
      containers:
        - name: api
          envFrom:
            - secretRef: { name: astradesk-secrets }
```

<br>

---

## 6) Ochrona danych (PII/Secrets)

- **At‑rest**: szyfrowanie DB (RDS), S3 (SSE‑S3/KMS), dyski EBS.  
- **In‑transit**: TLS/mTLS; h2c zakazane poza mesh.  
- **Minimalizacja**: przechowuj tylko to co potrzebne; pseudonimizuj identyfikatory.  
- **Maskowanie logów**: filtry dla pól jak `email`, `token`, `api_key`.

### Przykład - maskowanie w logach (Python)
```python
SENSITIVE_KEYS = {"password","token","api_key","authorization"}
def scrub(d: dict) -> dict:
    return {k: ("***" if k.lower() in SENSITIVE_KEYS else v) for k,v in d.items()}
```

<br>

---

## 7) Audyt i zgodność

- **Audyt**: trwały zapis do Postgres (`audits`) i publikacja do NATS.  
- **Archiwizacja**: `auditor` zapisuje JSON‑Lines do S3 **(WORM - Object Lock)**.  
- **Analiza**: Elasticsearch/Kibana lub OpenSearch.  
- **Retencja**: polityki retencji/ILM; dostęp kontrolowany przez IAM/role.

### Przykład - S3 bucket policy (WORM + versioning, skrót)

```hcl
resource "aws_s3_bucket" "audit" {
  bucket        = "astradesk-audit-prod"
  force_destroy = false
  versioning { enabled = true }
  object_lock_configuration {
    object_lock_enabled = "Enabled"
    rule {
      default_retention {
        mode  = "COMPLIANCE"
        days  = 365
      }
    }
  }
}
```

<br>

---

## 8) Rate limiting i odporność

- **Ingress/Envoy**: limit RPS, burst; nagłówek `Retry-After`.  
- **Client‑side**: backoff (pełny jitter), circuit breaker, timeouts.  
- **LLM**: obsługa 429/5xx przez wyjątki `ProviderOverloaded`/`ProviderServerError` z `suggested_sleep()`.

<br>

---

## 9) Guardrails LLM (treść i format)

- **Blocklist** (regex) dla promptów planera.  
- **Max length**: ucinanie zbyt długich promptów/odpowiedzi.  
- **Walidacja JSON**: plan jako lista kroków narzędziowych (schema).  
- **Bezpieczeństwo promptów**: unikanie wstrzyknięć (prompt injection) przez filtrowanie i kontekst ograniczony do RAG.

### Przykład - walidacja planu (JSON Schema, fragment)

```json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "type":"object",
  "properties": {
    "steps": {
      "type":"array",
      "items":{
        "type":"object",
        "required":["tool","args"],
        "properties":{
          "tool":{"type":"string","enum":["create_ticket","get_metrics","restart_service","get_weather"]},
          "args":{"type":"object"}
        }
      }
    }
  },
  "required":["steps"]
}
```

<br>

---

## 10) Kubernetes Security

- **RBAC**: role/rolebinding minimalnego zakresu; brak `cluster-admin` dla usług.  
- **Pod Security**: `restricted` (PSA/OPA/Gatekeeper), bez root, `readOnlyRootFilesystem`.  
- **Seccomp/AppArmor**: profile ograniczające syscalle.  
- **Capabilities**: drop `ALL`, dodaj tylko wymagane.  
- **Image policy**: tylko z zaufanego rejestru; podpisy (cosign) rekomendowane.


### Pod (fragment) - securityContext

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  fsGroup: 10001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  seccompProfile: { type: RuntimeDefault }
```

<br>

---

## 11) Łańcuch dostaw (Supply Chain)

- **SBOM**: `syft` generuje, `grype` skanuje; raport w artefaktach CI.  
- **Zależności**: skan `pip/audit`, `npm audit`, `gradle --scan`.  
- **Podpisy obrazów**: `cosign sign` + weryfikacja przy deploy (Policy Controller).  
- **Pinned versions**: lockfile (`uv.lock`/`package-lock.json`/`gradle.lockfile`).

<br>

---

## 12) Nagłówki HTTP / CORS / CSP

- **CORS**: whitelist domen; `credentials` tylko gdy konieczne.  
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Strict-Transport-Security` (na ingress).  
- **CSP**: dopasowana do portalu (blok skryptów zewnętrznych ograniczony).

### Ingress NGINX - przykładowe nagłówki

```yaml
nginx.ingress.kubernetes.io/configuration-snippet: |
  more_set_headers "X-Content-Type-Options: nosniff";
  more_set_headers "X-Frame-Options: DENY";
  more_set_headers "Referrer-Policy: no-referrer";
  more_set_headers "Permissions-Policy: geolocation=(), microphone=()";
```

<br>

---

## 13) Reagowanie na incydenty (IR) i forensyka

- **Detekcja**: alerty Grafana/Prometheus (5xx/429/latencja), logi sentinelowe, sygnały z SIEM.  
- **Triaż**: klasyfikacja (P1–P3), koordynacja przez on‑call.  
- **Zbieranie artefaktów**: snapshoty logów, kopie audytu S3, hashe obrazów, wersje chartów.  
- **Post‑mortem**: RCA, działania naprawcze, aktualizacja runbooków i polityk.

<br>

---

## 14) Zgodność i prywatność

- **PII/PHI**: minimalizacja, legal basis, rejestr przetwarzania, DPIA (jeśli wymagane).  
- **Retention**: polityki dla DB/S3/ES; żądania usunięcia danych (Right to Erasure).  
- **Dostęp**: kontrole IAM, MFA dla operatorów, least privilege dla ról.

<br>

---

## 15) Checklist bezpieczeństwa (skrót)

**Przed wdrożeniem prod:**
- [ ] mTLS STRICT (mesh), NetworkPolicy aktywne
- [ ] OIDC/JWKS: testy exp/nbf/iss/aud i clock‑skew
- [ ] RBAC narzędzi: test pozytywny/negatywny (`sre`, `it.support`, brak roli)
- [ ] S3: versioning + Object Lock (WORM) na bucket audytu
- [ ] SBOM wygenerowany, skan podatności bez HIGH/CRITICAL
- [ ] Secrets w Secret Manager/Vault, brak w repo
- [ ] Alerty P95 latencja, 5xx, 429, brak audytów
- [ ] Backup/DR: test odtwarzania (DB/S3/ES)

**Cyklicznie (miesięcznie/kwartalnie):**
- [ ] Rotacja kluczy API/LLM, weryfikacja uprawnień IAM
- [ ] Test scenariuszy IR (table‑top), przegląd logów/anomalii
- [ ] Przegląd polityk RBAC/ABAC i guardrails LLM

<br>

---

**Wersja dokumentu:** 1.0.0  
**Właściciel:** Zespół Bezpieczeństwa / SRE AstraDesk  
**Kontakt on‑call:** #astradesk‑sec @ Slack / rota PagerDuty