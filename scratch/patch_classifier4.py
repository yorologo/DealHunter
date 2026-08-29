with open("scratch/classifier.py", "r") as f:
    content = f.read()

content = content.replace("if ratio_min >= 0.8 and ratio_max >= 0.7:", "if ratio_min >= 0.75 and ratio_max >= 0.65:")

with open("scratch/classifier.py", "w") as f:
    f.write(content)
