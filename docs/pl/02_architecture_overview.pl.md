![AstraDesk](../assets/astradesk-logo.svg)

# 2. Przegląd Architektury

> AstraDesk rozdziela **kontrolę** (Gateway, Catalog, Policy) od **wykonania** (Agenci + Narzędzia) i **dowodów** (AstraOps).  
> Wersja: Framework 1.0 (skupienie na pojedynczym agencie z human-in-the-loop).

## 2.1 Cele i Nie-Cele (v1.0)

- **Cele**  
  - Bezpieczny, obserwowalny runtime pojedynczego agenta (SupportAgent/OpsAgent).  
  - Integracje **MCP-first** przez AstraDesk Gateway (authZ, OPA, limity częstotliwości, audit).  
  - Telemetria i ewaluacje przez **AstraOps** (ślady, metryki, ewaluacje offline/online).  
  - **AstraCatalog** dla własności, poziomu ryzyka, wersji, artefaktów certyfikacji.

- **Nie-Cele**  
  - Orkiestracja roju wielu agentów (planowane w v2.0).  
  - Automatyczna modyfikacja promptów w produkcji bez bramek zatwierdzających.  
  - Nieograniczone uprawnienia narzędzi (wszystkie narzędzia wymagają jawnego zakresu i klasy efektów ubocznych).

<br>

---

## 2.2 Diagram Systemu Wysokiego Poziomu

```mermaid
%%{
  init: {
    "theme": "base",
    "themeVariables": {
      "background": "#FFFFFF",
      "lineColor": "#111827",
      "textColor": "#0f172a",
      "clusterBkg": "#FFFFFF",
      "clusterBorder": "#CBD5E1",
      "fontFamily": "Inter, ui-sans-serif, system-ui"
    }
  }
}%%
flowchart LR
  %% =============== SUBGRAFY ===============
  subgraph Clients["Klienci i Integracje"]
    U1[Panel Admin]:::c
    U2[Slack/Chat UI]:::c
    U3[API Serwisów]:::c
  end

  subgraph Gateway["AstraDesk Gateway"]
    GI[MCP Ingress<br/>OIDC · RBAC · OPA · Limity · Audit]:::g
    GL[LLM Gateway<br/>Routing · Cache · Pomiar Kosztów]:::g
  end

  subgraph Runtime["Runtime Agentów"]
    A1[SupportAgent]:::a
    A2[OpsAgent]:::a
  end

  subgraph Ops["AstraOps"]
    T1[Ślady/Logi/Metryki]:::o
    E1["Ewaluacje<br/>offline / online / in-loop"]:::o
    D1[Dashboardy/Alerty]:::o
  end

  subgraph Catalog["AstraCatalog"]
    R1[Rejestr<br/>Agenci/Narzędzia/Prompty]:::k
    P1[Polityki i Poziom Ryzyka]:::k
    C1[Artefakty Certyfikacji]:::k
  end

  subgraph Data["Dane Korporacyjne i Narzędzia"]
    DB[(PostgreSQL 18)]:::d
    VDB[(Vector/Graph DB)]:::d
    OBJ[(Object Storage/S3)]:::d
    BUS[(NATS/Kafka)]:::d
    EXT[(Zewnętrzne API przez MCP)]:::d
  end

  %% =============== PRZEPŁYWY ===============
  U1 --> GI
  U2 --> GI
  U3 --> GI

  GI --> A1
  GI --> A2
  GL --> A1

  A1 <--> T1
  A2 <--> T1
  A1 --> E1
  A2 --> E1
  T1 --> D1

  A1 --> DB
  A1 --> VDB
  A1 --> OBJ
  A1 --> BUS
  A1 --> EXT

  A2 --> DB
  A2 --> VDB
  A2 --> OBJ
  A2 --> BUS
  A2 --> EXT

  Ops --> Catalog
  Catalog --> GI

  %% Wzmocnione krawędzie (widoczne w dark mode)
  linkStyle default stroke:#111827,stroke-width:2px,opacity:1;

  %% =============== STYLE ===============
  style Clients fill:#F1F5FF,stroke:#A5B4FC,stroke-width:1px,color:#0f172a
  style Gateway fill:#ECFDF5,stroke:#34D399,stroke-width:1px,color:#064E3B
  style Runtime fill:#F0FDF4,stroke:#86EFAC,stroke-width:1px,color:#14532D
  style Ops fill:#FFF7ED,stroke:#FDBA74,stroke-width:1px,color:#7C2D12
  style Catalog fill:#FDF4FF,stroke:#F0ABFC,stroke-width:1px,color:#4A044E
  style Data fill:#F8FAFC,stroke:#94A3B8,stroke-width:1px,color:#0f172a

  classDef c fill:#E3F2FD,stroke:#2962FF,stroke-width:2px,color:#0D47A1;
  classDef g fill:#E8F5E9,stroke:#16A34A,stroke-width:2px,color:#065F46;
  classDef a fill:#ECFEF3,stroke:#22C55E,stroke-width:2px,color:#065F46;
  classDef o fill:#FFF1E6,stroke:#FB923C,stroke-width:2px,color:#7C2D12;
  classDef k fill:#FAF5FF,stroke:#D946EF,stroke-width:2px,color:#4A044E;
  classDef d fill:#EFF6FF,stroke:#60A5FA,stroke-width:2px,color:#0C4A6E;
```

<br>

<br>

---

## 2.3 Odpowiedzialności Komponentów

<br>

### AstraDesk Gateway

- **Tożsamość i Dostęp**: OIDC/OAuth2 dla agentów i narzędzi; RBAC per narzędzie z allow-listami parametrów.

- **Wymuszanie Polityk**: zabezpieczenia OPA/Rego; routing środowiskowy (dev/stage/prod).

- **Limity Częstotliwości i Kwoty**: per tenant/agent/narzędzie; backpressure i circuit breakers.

- **Audit**: wszystkie wywołania narzędzi MCP podpisane z digestami żądań/odpowiedzi.

<br>

### Runtime Agentów (SupportAgent/OpsAgent)

- **Rozumowanie i Planowanie** (v1.0): deterministyczny planer + opcja LLM; jawne granice **akceptowalnej autonomii**.

- **Pamięć**: efemeryczna pamięć zadań z TTL; opcjonalne wyszukiwania vector/graph (domyślnie tylko odczyt).

- **Narzędzia**: narzędzia MCP z zadeklarowanymi efektami ubocznymi (`read|write|execute`) i schematami.

- **Human-in-the-loop**: punkty zatwierdzania dla akcji `write/execute`.

<br>

### AstraOps

- **Ślady** przepływów agentowych: prompt → plan → wywołania narzędzi → efekty uboczne → odpowiedź.

- **Metryki**: p95 opóźnienia, sukces narzędzi, proxy ugruntowania, koszt per zadanie.

- **Ewaluacje**: CI/offline, produkcja/online i bramki **in-loop** (np. trafność kontekstu).

<br>

### AstraCatalog

- **Rejestr**: agenci, narzędzia, prompty, datasety, trasy modeli.

- **Ryzyko i Polityki**: per wersja agenta; kontrole zmian; metadane kill-switch.

- **Certyfikacja**: artefakty dla wdrożenia (wyniki eval, notatki red-team, wskaźniki SBOM).

<br>

### Dane i Narzędzia

- **PostgreSQL 16→18**: system referencyjny (odczyt/zapis przez zarządzane narzędzia).

- **Vector/Graph DB**: wyszukiwanie i relacje; domyślnie tylko odczyt w v1.0.

- **Magistrale**: NATS/Kafka dla zdarzeń i zadań async; idempotentne handlery.

- **Zewnętrzne API**: tylko przez zarejestrowane serwery MCP z zakresowymi tokenami.

<br>

---

## 2.4 Sekwencja: Żądanie → Wynik (Happy Path)

<br>

```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'actorBkg': '#E3F2FD',
      'actorBorder': '#2962FF',
      'actorTextColor': '#0D47A1',
      'signalColor': '#AA00FF',
      'signalTextColor': '#737d8bff',
      'activationBkgColor': '#FFE082',
      'activationBorderColor': '#FFAB00',
      'background': '#FFFFFF'
    }
  }
}%%
sequenceDiagram
  participant C as Klient
  participant GW as AstraDesk Gateway
  participant AG as Agent
  participant TS as Serwer Narzędzi MCP
  participant OP as AstraOps

  rect rgba(41,98,255,0.08)
    C->>GW: Żądanie (JWT, kontekst)
    GW->>AG: Dispatch (zakresowa autentykacja + polityki)
  end

  AG->>AG: Plan (deterministyczny/LLM)

  rect rgba(170,0,255,0.08)
    AG->>GW: wywołaj(narzędzie, args, efekt_uboczny)
    GW->>TS: Zakresowe wywołanie + sprawdzenie OPA
    TS-->>GW: Wynik
    GW-->>AG: Wynik + id audytu
  end

  AG->>OP: Ślady + Metryki
  AG-->>C: Finalna odpowiedź (opcjonalne wyjaśnienie)
```

<br>

<br>

---

## 2.5 Widoki Wdrożenia (Kubernetes/EKS)

<br>

```mermaid
%%{
  init: {
    "theme": "base",
    "themeVariables": {
      "background": "#FFFFFF",
      "lineColor": "#111827",
      "textColor": "#0f172a",
      "fontFamily": "Inter, ui-sans-serif, system-ui"
    },
    "flowchart": {
      "htmlLabels": true,
      "curve": "linear",
      "nodeSpacing": 90,
      "rankSpacing": 150
    }
  }
}%%
flowchart TB
  %% ================= SUBGRAFY =================
  subgraph ControlPlane["Płaszczyzna Kontroli (Namespace:&nbsp;astra-control)"]
    GWD[Gateway Deployment]:::gateway
    CTG[Catalog API]:::api
    OPA[OPA / Kontroler Polityk]:::policy
  end

  subgraph Agents["Obciążenie (Namespace:&nbsp;astra-agents)"]
    SA[SupportAgent]:::agent
    OA[OpsAgent]:::agent
  end

  subgraph Telemetry["Obserwowalność (Namespace:&nbsp;astra-ops)"]
    OTEL[Kolektor OpenTelemetry]:::observ
    PRM[Prometheus]:::observ
    GRF[Grafana]:::observ
  end

  %% ================= PRZEPŁYWY =================
  GWD --> SA
  GWD --> OA
  SA --> OTEL
  OA --> OTEL
  OTEL --> PRM --> GRF
  CTG --> GWD
  OPA --> GWD

  %% Wyraźne krawędzie (czytelne w dark mode)
  linkStyle default stroke:#111827,stroke-width:2px,opacity:1

  %% ================= STYLE =================
  style ControlPlane fill:#F0F9FF,stroke:#38BDF8,stroke-width:1px,color:#0C4A6E
  style Agents      fill:#ECFDF5,stroke:#34D399,stroke-width:1px,color:#064E3B
  style Telemetry   fill:#FEF3C7,stroke:#F59E0B,stroke-width:1px,color:#7C2D12

  classDef gateway fill:#DBEAFE,stroke:#2563EB,stroke-width:2px,color:#1E3A8A,rx:8,ry:8
  classDef api     fill:#EDE9FE,stroke:#7C3AED,stroke-width:2px,color:#4C1D95,rx:8,ry:8
  classDef policy  fill:#FFE4E6,stroke:#FB7185,stroke-width:2px,color:#881337,rx:8,ry:8
  classDef agent   fill:#DCFCE7,stroke:#22C55E,stroke-width:2px,color:#14532D,rx:8,ry:8
  classDef observ  fill:#FEF9C3,stroke:#EAB308,stroke-width:2px,color:#854D0E,rx:8,ry:8
```

<br>

---

## 2.6 Poziom Bezpieczeństwa (v1.0)

* **Najmniejsze Uprawnienia** dla każdego narzędzia MCP; jawna klasa efektów ubocznych wymuszana na bramce.

* **Izolacja Środowisk**: dev/stage/prod z oddzielnymi poświadczeniami i pakietami polityk.

* **Łańcuch Dostaw**: podpisane obrazy kontenerów; załączony SBOM; polityki admission blokują nieznane digesty.

* **Dane**: sekrety w managerze (KMS/ASM), filtry PII na wejściu, allow-listy na wyjściu.

<br>

---

## 2.7 Model Obserwowalności

* **Ślady**: span per krok planu i per wywołanie narzędzia; ID korelacji przez gateway/agent/narzędzie.

* **Metryki**: SLO (p95 opóźnienia), KPI biznesowe (containment, rozwiązanie), KPI bezpieczeństwa (naruszenia polityk).

* **Dashboardy**: widoki operatora i właściciela; playbooki triage → RCA; kontrola zmęczenia alertami.

<br>

---

## 2.8 Rozszerzalność i Punkty Zaczepienia Mapy Drogowej

* **Orkiestracja wielu agentów** przez router świadomy polityk (v2.0).

* **Pamięć AstraGraph** z czasowym zanikaniem i wyszukiwaniem świadomym relacji (v2.0).

* **Routing modeli świadomy kosztów** (p95 + limity cenowe) w LLM Gateway.

<br>

---

## 2.9 Odniesienia Krzyżowe

* Dalej: [3. Faza Planowania](03_plan_phase.pl.md)

* Wstecz: [1. Wprowadzenie](01_introduction.pl.md)

* Zobacz także: [8. Bezpieczeństwo i Governance](08_security_governance.pl.md), [7. Monitorowanie i Operowanie](07_monitor_operate.pl.md)

<br>