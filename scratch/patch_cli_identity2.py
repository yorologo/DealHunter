with open("src/dealhunter/cli.py", "r") as f:
    content = f.read()

handler_def = """
    if args.command == "identity":
        if args.action == "evaluate":
            if getattr(args, 'shadow', False):
                from dealhunter.identity.evaluator import evaluate_shadow
                evaluate_shadow(db_path)
            else:
                print("Production evaluation not enabled. Use --shadow.")
        return

"""
content = content.replace('    if args.command == "comparison":', handler_def + '    if args.command == "comparison":')

with open("src/dealhunter/cli.py", "w") as f:
    f.write(content)
