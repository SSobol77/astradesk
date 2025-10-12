![AstraDesk](../assets/astradesk-logo.svg)

# 1. Wprowadzenie - Wizja AstraDesk

> AstraDesk Enterprise AI Framework v1.0 - Przewodnik Techniczny (PL)

**AstraDesk** to bezpieczny, modularny framework do budowania **korporacyjnych agentów AI**, które rozumują, planują i działają za pomocą narzędzi.
Operacjonalizuje *AgentOps* (obserwowalność + ewaluacja), *governance* oraz *DevSecOps* specjalnie dla systemów agentowych.

<br>

## Dlaczego AstraDesk teraz

- Od deterministycznego kodu → do pętli probabilistycznego rozumowania.

- Od statycznych przepływów pracy → do adaptacyjnych, celowych agentów.

- Od podejścia "kod najpierw" → do **"ewaluacja najpierw"** (wdrażaj z dowodami, nie intuicją).

<br>

## Co zawiera v1.0

- Runtime dla pojedynczego agenta (SupportAgent / OpsAgent) z funkcją human-in-the-loop.

- Integracje oparte na MCP (narzędzia/zasoby/prompty) przez **AstraDesk Gateway**.

- **AstraOps** do śledzenia, metryk, ewaluacji; **AstraCatalog** do zarządzania właścicielstwem, ryzykiem i wersjami.

- Wdrożenia hybrydowe: AWS/Kubernetes/OpenShift/on-prem; PostgreSQL 18; OpenTelemetry.

<br>

## Mapa dokumentacji

> - 2. Przegląd Architektury → ogólny obraz
>
> - 3. (3.-7.) ADLC → planowanie, budowanie, testowanie/optymalizacja, wdrażanie, operowanie
>
> - 8. Bezpieczeństwo i Governance
>
> - 9. MCP Gateway i Pakiety Domenowe
>
> - 10. Przyszła Mapa Drogowa i Słowniczek

<br>

<br>


## Szkic architektury wysokiego poziomu (kontekst)

<br>

```mermaid

flowchart LR
  subgraph GW["AstraDesk Gateway"]
    G1[MCP Ingress]
    G2[LLM Gateway]
  end
  subgraph RT["Runtime Agentów"]
    A1[SupportAgent]
    A2[OpsAgent]
  end
  subgraph OPS["AstraOps"]
    O1[Ślady]
    O2[Ewaluacje]
  end
  subgraph CAT["AstraCatalog"]
    C1[Rejestr]
    C2[Polityki]
  end
  subgraph DATA["Dane/Narzędzia"]
    D1[(PostgreSQL 18)]
    D2[(Vector/Graph DB)]
    D3[(Zewnętrzne API)]
  end
  G1 --> A1
  G1 --> A2
  A1 <-->|sygnały| OPS
  A2 <-->|sygnały| OPS
  A1 --> DATA
  A2 --> DATA
  OPS --> CAT
  CAT --> G1
```

<br>


**Dalej:** [2. Przegląd Architektury](02_architecture_overview.pl.md)