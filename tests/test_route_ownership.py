from dealhunter.web.app import create_app

def test_route_ownership_best_and_deals():
    app = create_app()
    deals_endpoints = [r.endpoint for r in app.url_map.iter_rules() if r.rule == '/deals']
    best_endpoints = [r.endpoint for r in app.url_map.iter_rules() if r.rule == '/best']
    
    # Assert EXACTLY one ownership for /deals and /best
    assert len(deals_endpoints) == 1, f"Expected 1 endpoint for /deals, got {len(deals_endpoints)}: {deals_endpoints}"
    assert deals_endpoints[0] == 'deals', f"Expected /deals to map to 'deals', got {deals_endpoints[0]}"
    
    assert len(best_endpoints) == 1, f"Expected 1 endpoint for /best, got {len(best_endpoints)}: {best_endpoints}"
    assert best_endpoints[0] == 'best', f"Expected /best to map to 'best', got {best_endpoints[0]}"
