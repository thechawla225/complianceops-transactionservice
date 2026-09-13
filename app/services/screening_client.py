 
from dataclasses import dataclass
 
import httpx
from fastapi import HTTPException
 
from app.config import settings
 
 
@dataclass
class ScreeningResult:
    status: str 
    screening_ref: str
 
 
async def screen(debtor_name: str, creditor_name: str) -> ScreeningResult:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.screening_service_url}/screen",
                json={"debtorName": debtor_name, "creditorName": creditor_name},
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="screening service unreachable") from exc
        resp.raise_for_status()
        body = resp.json()
        return ScreeningResult(status=body["verdict"], screening_ref=body["screeningRef"])