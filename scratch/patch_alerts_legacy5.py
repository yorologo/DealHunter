with open("src/dealhunter/alerts.py", "r") as f:
    content = f.read()

content = content.replace('"price": r[7],', '"current_price": r[7],')

with open("src/dealhunter/alerts.py", "w") as f:
    f.write(content)

with open("tests/test_alerts.py", "r") as f:
    content = f.read()

# Let's just make sure tests pass. They were checking res3[0]["current_price"].

with open("tests/test_alerts.py", "w") as f:
    f.write(content)
