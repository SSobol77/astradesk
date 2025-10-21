# dev/mock_tickets.py
# Minimalny adapter zgłoszeń do dev: nasłuchuje na /api/tickets i zwraca syntetyczny ID.
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import uuid

app = FastAPI(title="Mock Ticket Adapter")

class TicketIn(BaseModel):
    title: str
    body: str | None = None

@app.post("/api/tickets")
def create_ticket(t: TicketIn):
    tid = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    return {
        "id": tid,
        "title": t.title,
        "url": f"http://localhost:8082/tickets/{tid}"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
