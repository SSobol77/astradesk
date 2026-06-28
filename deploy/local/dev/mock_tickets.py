# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/local/dev/mock_tickets.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for deploy/local/dev/mock_tickets.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

# dev/mock_tickets.py
# Minimalny adapter zgłoszeń do dev: nasłuchuje na /api/tickets i zwraca syntetyczny ID.
import uuid

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title='Mock Ticket Adapter')


class TicketIn(BaseModel):
    title: str
    body: str | None = None


@app.post('/api/tickets')
def create_ticket(t: TicketIn):
    tid = f'TCK-{uuid.uuid4().hex[:8].upper()}'
    return {'id': tid, 'title': t.title, 'url': f'http://localhost:8082/tickets/{tid}'}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8082)
