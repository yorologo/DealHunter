import json
import csv
import sys

def print_results(results, format="table", output_file=None, compact=False):
    if format == "json":
        out = json.dumps(results, indent=2, ensure_ascii=False)
        _write(out, output_file)
    elif format == "csv":
        if not results:
            return
        import io
        si = io.StringIO()
        writer = csv.DictWriter(si, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        _write(si.getvalue(), output_file)
    elif format == "markdown":
        if not results:
            _write("No results found.", output_file)
            return
        keys = list(results[0].keys())
        lines = []
        lines.append("| " + " | ".join(keys) + " |")
        lines.append("|" + "|".join(["---"] * len(keys)) + "|")
        for r in results:
            lines.append("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")
        _write("\n".join(lines), output_file)
    else: # table
        if not results:
            _write("No results found.", output_file)
            return
        if compact:
            lines = []
            for r in results:
                # assuming fields like current_discount_effective, current_price, store_name, product_name
                d = r.get("current_discount_effective", r.get("discount_effective", 0))
                p = r.get("current_price", r.get("price", 0))
                s = r.get("store_name", "")
                n = r.get("product_name", r.get("name", ""))
                lines.append(f"{d:.1f}% | ${p:.2f} | {s} | {n}")
            _write("\n".join(lines), output_file)
        else:
            # basic table
            keys = list(results[0].keys())
            fmt = "{:<15} " * len(keys)
            lines = [fmt.format(*keys)]
            for r in results:
                vals = [str(r.get(k, ""))[:14] for k in keys]
                lines.append(fmt.format(*vals))
            _write("\n".join(lines), output_file)

def _write(content, output_file):
    if output_file:
        with open(output_file, "w") as f:
            f.write(content)
    else:
        print(content)
