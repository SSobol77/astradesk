# Schemat

```sh
.
├── datasets/ 
│   ├── README.md             # Opisuje, jak dodawać i zarządzać datasetami
│   │
│   ├── support/              # Dane wejściowe TYLKO dla SupportAgent
│   │   ├── faq_vpn.md
│   │   ├── procedura_reset_hasla.txt
│   │   └── runbooki/
│   │       └── restart_uslugi_platnosci.md
│   │
│   └── ops/                  # Dane wejściowe TYLKO dla OpsAgent
│       ├── polityka_bezpieczenstwa.md
│       └── standardy_wdrozen_k8s.txt
│
├── docs/                     # Bez zmian - pozostaje TYLKO dla dokumentacji projektu
│   └── ...
│
├── scripts/
│   └── ingest_docs.py        # Zmienimy ten skrypt
│
└── Makefile                  # Zmienimy komendę `ingest`

```