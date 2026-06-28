<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: datasets/README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

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
