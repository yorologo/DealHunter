import csv
import io
import json

from dealhunter.output import print_results


SAMPLE = [
    {"provider": "rappi", "product_name": "Café molido", "price": 99.5},
    {"provider": "uber_eats", "product_name": "Té verde", "price": 88.0},
]


def test_public_json_output_is_array_of_rows(capsys):
    print_results(SAMPLE, format="json")
    payload = json.loads(capsys.readouterr().out)
    assert payload == SAMPLE


def test_public_csv_output_preserves_header_order_and_values(capsys):
    print_results(SAMPLE, format="csv")
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert list(rows[0]) == list(SAMPLE[0])
    assert rows == [
        {"provider": "rappi", "product_name": "Café molido", "price": "99.5"},
        {"provider": "uber_eats", "product_name": "Té verde", "price": "88.0"},
    ]


def test_empty_machine_outputs_are_stable(capsys):
    print_results([], format="json")
    assert json.loads(capsys.readouterr().out) == []
    print_results([], format="csv")
    assert capsys.readouterr().out == ""
