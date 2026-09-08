# Creating a temporary Stub

from dataclasses import dataclass


@dataclass
class ScreeningResult:
    status: str
    screening_ref: str


def screen(debtor_name: str, creditor_name: str) -> ScreeningResult:
    return ScreeningResult(status="clear", screening_ref="SCR-STUB-0001")