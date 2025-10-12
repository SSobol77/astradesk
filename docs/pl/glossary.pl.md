![AstraDesk](../assets/astradesk-logo.svg)


# Słowniczek

> Podstawowe terminy używane w dokumentacji AstraDesk Framework 1.0.

- **ADLC** - *Agent Development Lifecycle* (Cykl Życia Rozwoju Agenta): Plan → Budowa → Test/Optymalizacja → Wdrożenie → Monitor/Operowanie.

- **AstraOps** - Narzędzia i dashboardy obserwowalności + ewaluacji, które odpowiadają na pytanie *"Czy jest poprawny?"*.

- **AstraCatalog** - Rejestr agentów, narzędzi, promptów, datasetów, poziomu ryzyka i artefaktów certyfikacji.

- **Gateway** - Punkt wejściowy płaszczyzny kontroli dla narzędzi MCP i routingu LLM z OPA, kwotami i audytem.

- **MCP** - *Model Context Protocol* (Protokół Kontekstu Modelu) dla narzędzi/zasobów/promptów odkrywanych i wywoływanych przez agentów.

- **OPA/Rego** - Silnik i język polityki jako kod używany do bramkowania efektów ubocznych i reguł egress danych.

- **Acceptable Agency** (Akceptowalna Autonomia) - Jawne limity uprawnień dla agenta; chroni efekty uboczne `read|write|execute`.

- **Groundedness** (Ugruntowanie) - Stopień w jakim odpowiedź jest wspierana przez dostarczony kontekst/dowody.

- **Containment** (Zawieranie) - % przypadków rozwiązanych bez przekazania człowiekowi (KPI biznesowe).

- **SLO** - *Service Level Objective* (Cel Poziomu Usługi) (np. opóźnienie p95 ≤ 8s, sukces narzędzi ≥ 95%).

- **Champion–Challenger** - Kontrolowana promocja gdzie nowa wersja musi przewyższyć obecną na tych samych ewaluacjach.

- **Schema Pinning** (Przypinanie Schematu) - Wymaganie hashu schematu narzędzia przy każdym wywołaniu; Gateway odrzuca niezgodności.

- **Shadow/Canary** - Uruchamianie challengera na lustrzanym ruchu (shadow) lub progresywne przesuwanie żywego ruchu (canary).

- **Judge Kernel** (Kernel Sędziego) - Podłączalna rubryka/model który ocenia pomocność, bezpieczeństwo, ugruntowanie dla bramkowania in-loop.

- **AstraGraph Memory** (Pamięć AstraGraph) - Planowana hybrydowa pamięć vector + graph z czasowym zanikaniem i pochodzeniem (v2.0).

<br>

---

## Odniesienia Krzyżowe

- Zobacz: [2. Przegląd Architektury](02_architecture_overview.pl.md)  

- Także: [8. Bezpieczeństwo i Governance](08_security_governance.pl.md), [5. Testowanie i Optymalizacja](05_test_optimize.pl.md), [7. Monitorowanie i Operowanie](07_monitor_operate.pl.md)

<br>
