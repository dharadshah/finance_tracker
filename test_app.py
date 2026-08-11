from finance_tracker.api.main import app
print('Total routes:', len(app.routes))
for route in app.routes:
    if hasattr(route, 'methods') and 'mf' in route.path:
        print(route.methods, route.path)