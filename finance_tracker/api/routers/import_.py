from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import tempfile
import os
from pathlib import Path

from finance_tracker.services.import_service import ImportService
from finance_tracker.parsers.registry import available_parsers, PARSER_REGISTRY

router = APIRouter(prefix="/api/import", tags=["import"])


# Schemas
class ImportSummaryResponse(BaseModel):
    account_name: str
    institution: str
    account_number_masked: str | None
    statement_period: str
    transactions_inserted: int
    transactions_skipped: int
    total_processed: int
    warnings: list[str]
    errors: list[str]
    success: bool


class ParserInfo(BaseModel):
    key: str
    institution: str


# Routes
@router.get("/parsers", response_model=list[ParserInfo])
def list_parsers():
    return [
        ParserInfo(key=k, institution=PARSER_REGISTRY[k].INSTITUTION)
        for k in available_parsers()
    ]


@router.post("/", response_model=ImportSummaryResponse)
async def import_statement(
    file: UploadFile = File(...),
    parser_key: str = Form(...),
    account_id: int = Form(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        service = ImportService()
        summary = service.import_statement(
            file_path=tmp_path,
            parser_key=parser_key,
            account_id=account_id,
        )
    finally:
        os.unlink(tmp_path)

    return ImportSummaryResponse(
        account_name=summary.account_name,
        institution=summary.institution,
        account_number_masked=summary.account_number_masked,
        statement_period=summary.statement_period,
        transactions_inserted=summary.transactions_inserted,
        transactions_skipped=summary.transactions_skipped,
        total_processed=summary.total_processed,
        warnings=summary.warnings,
        errors=summary.errors,
        success=summary.success,
    )