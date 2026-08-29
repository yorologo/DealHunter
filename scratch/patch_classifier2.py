with open("scratch/classifier.py", "r") as f:
    content = f.read()

content = content.replace("if ratio_max == 1.0:", "if ratio_min == 1.0 and ratio_max >= 0.7:")

with open("scratch/classifier.py", "w") as f:
    f.write(content)
