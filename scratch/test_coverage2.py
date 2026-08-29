from patch_package import parse_package

cases = [
    "600 ml",
    "0.6 L",
    "1 kg",
    "1000 g",
    "1,5 L",
    "8 x 42.5 g",
    "8 und / 340 g",
    "12 pack 355 ml",
    "10+2 sobres",
    "4 piezas",
    "2 x 600 ml",
    "1.2 L bottle"
]

for c in cases:
    print(f"'{c}' -> {parse_package(c, None, None)}")
