from finance_tracker.database import get_session
from finance_tracker.services.mf_import_service import MFImportService

with get_session() as session:
    svc = MFImportService()
    count = svc._rebuild_holdings(session, 4)
    print('Holdings rebuilt:', count)