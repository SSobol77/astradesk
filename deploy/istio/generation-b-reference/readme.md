<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: deploy/istio/generation-b-reference/readme.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

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
