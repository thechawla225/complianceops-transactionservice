import json
import logging
from functools import lru_cache

import boto3
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from app.config import settings

log = logging.getLogger(__name__)


@lru_cache
def _client():
    # No explicit credentials: on EKS boto3 picks up IRSA (transaction-sa -> complianceops-transaction-sqs-role)
    return boto3.client("sqs", region_name=settings.aws_region)


async def publish_flagged(txn, matched_entity: str | None) -> None:
    """Send a flagged transaction to SQS for the notifier (fields match its messageParser)."""
    if not settings.sqs_queue_url:
        log.warning("SQS_QUEUE_URL not set; not publishing flagged transaction %s", txn.id)
        return
    body = {
        "transactionId": str(txn.id),
        "endToEndId": txn.end_to_end_id,
        "debtorName": txn.debtor_name,
        "creditorName": txn.creditor_name,
        "instructedAmount": {"amount": str(txn.instructed_amount), "currency": txn.instructed_currency},
        "matchedEntity": matched_entity,
        "screeningRef": txn.screening_ref,
    }
    try:
        # boto3 is synchronous, so run it off the event loop
        await run_in_threadpool(
            _client().send_message, QueueUrl=settings.sqs_queue_url, MessageBody=json.dumps(body)
        )
    except Exception as exc:
        # The transaction is already saved as flagged; fail loudly so the missing alert isn't silent
        log.exception("failed to publish flagged transaction %s", txn.id)
        raise HTTPException(status_code=502, detail="alert queue unavailable") from exc
