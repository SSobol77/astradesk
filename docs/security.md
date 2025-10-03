# Bezpieczeństwo

## OIDC/JWT
- API wymaga Bearer JWT; walidacja przez JWKS (issuer, audience).
- Portal przekazuje token do API.

## mTLS
- Włącz cert-manager i mesh (Istio/Linkerd).
- Ustaw PeerAuthentication (STRICT) i DestinationRule z TLS ISTIO_MUTUAL.
- Zewnętrzne ingressy: certyfikaty ACM/Let's Encrypt.

## RBAC dla tooli
- Polityki oparte o roles z tokena (claims), np. `ops_actions.restart_service` tylko dla `role: sre`.
- Wymuszaj polityki w warstwie toola lub w middleware.

## Audyt
- Każda akcja narzędzia → wpis w Postgres + event NATS → Auditor zapisuje do S3/Elasticsearch.
- S3 z versioning + KMS. Elasticsearch do szybkiej analizy.
