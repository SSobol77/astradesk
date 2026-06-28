// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: docs/js/mermaid-init.js
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for docs/js/mermaid-init.js.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

document.addEventListener('DOMContentLoaded', function () {
  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: true,
      securityLevel: 'loose' // pozwala na <br/> w etykietach węzłów itp.
    });
  }
});
