import traceback
try:
    from finance_tracker.api.routers import mutual_funds
    print('Loaded OK, routes:', len(mutual_funds.router.routes))
except Exception as e:
    traceback.print_exc()