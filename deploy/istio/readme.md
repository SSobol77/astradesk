# Jak zastosować

### 1) Namespace z injection
kubectl apply -f deploy/istio/00-namespace.yaml

### 2) mTLS i polityki
kubectl apply -f deploy/istio/10-peer-authentication.yaml
kubectl apply -f deploy/istio/20-destinationrule-astradesk-api.yaml
kubectl apply -f deploy/istio/30-authorizationpolicy-namespace.yaml

### 3) Gateway + VirtualService (+ cert jeśli używasz cert-manager)
kubectl apply -f deploy/istio/40-gateway.yaml
kubectl apply -f deploy/istio/41-virtualservice-astradesk-api.yaml
kubectl apply -f deploy/istio/50-cert-manager-certificate.yaml   # opcjonalnie
