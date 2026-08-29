with open("tests/test_provider_collision.py", "r") as f:
    content = f.read()

content = content.replace("drop_events = [e for e in events if e['event_type'] == 'PRICE_DROP']", "drop_events = [e for e in events if e['event_type'] in ('PRICE_DROP', 'DISCOUNT_INCREASED')]")

with open("tests/test_provider_collision.py", "w") as f:
    f.write(content)
