with open("tests/test_provider_collision.py", "r") as f:
    content = f.read()
    
# insert into runs
runs_insert = """
    # Insert runs
    c.execute("INSERT INTO runs (run_id, started_at) VALUES ('run1', '2026-08-01T09:00:00Z')")
    c.execute("INSERT INTO runs (run_id, started_at) VALUES ('run2', '2026-08-02T09:00:00Z')")
    
    # Observations Rappi
"""
content = content.replace("    # Observations Rappi\n", runs_insert)

with open("tests/test_provider_collision.py", "w") as f:
    f.write(content)
