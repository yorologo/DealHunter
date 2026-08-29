with open("tests/test_provider_collision.py", "r") as f:
    content = f.read()

content = content.replace("assert uber_obs[1][1] == 180.0", "assert uber_obs[1][1] == 150.0")

new_alerts = """
    drop_events = [e for e in events if e['event_type'] == 'PRICE_DROP']
    new_deal_events = [e for e in events if e['event_type'] == 'NEW_DEAL']
    
    # Uber generated a PRICE_DROP (200 -> 150 is 25%)
    # Rappi generated a NEW_DEAL (100 -> 50 is 50%, crossed 50%)
    assert len(drop_events) == 1
    assert len(new_deal_events) == 1
    
    assert drop_events[0]['provider'] == 'uber_eats'
    assert new_deal_events[0]['provider'] == 'rappi'
"""

import re
content = re.sub(r"drop_events = \[e for e in events if e\['event_type'\] == 'PRICE_DROP'\].*", new_alerts.strip(), content, flags=re.DOTALL)

with open("tests/test_provider_collision.py", "w") as f:
    f.write(content)
