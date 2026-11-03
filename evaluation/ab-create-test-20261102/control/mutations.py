"""Frozen, evaluator-only behavior mutations; never supplied to generators."""

MUTATIONS = {
    'M01': ("'title': args.title,", "'title': args.title.strip(),"),
    'M02': ("'category': args.category,", "'category': args.category.strip(),"),
    'M03': ('or args.cents <= 0:', 'or args.cents < 0:'),
    'M04': ('or args.cents <= 0:', 'or args.cents == 0:'),
    'M05': ("add.add_argument('--cents', type=int, required=True)",
            "add.add_argument('--cents', type=lambda value: int(float(value)), required=True)"),
    'M06': ("max((item['id'] for item in entries), default=0) + 1",
            "max((item['id'] for item in entries), default=-1) + 1"),
    'M07': ("max((item['id'] for item in entries), default=0) + 1",
            "len([item for item in entries if not item['voided']]) + 1"),
    'M08': ("    state.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\\n')",
            "    pass  # isolated regression: do not persist"),
    'M09': ("        entries.append(entry)", "        entries[:] = [entry]"),
    'M10': ("        result = entries", "        result = [item for item in entries if not item['voided']]"),
    'M11': ("        entry['voided'] = True",
            "        entry['voided'] = True\n        entries.remove(entry)"),
    'M12': ("        entry['voided'] = True",
            "        for item in entries:\n            item['voided'] = True"),
    'M13': ("        entry['voided'] = True",
            "        if entry['voided']:\n            print('already voided', file=sys.stderr)\n            return 1\n        entry['voided'] = True"),
    'M14': ("sum(item['cents'] for item in active)", "sum(item['cents'] for item in entries)"),
    'M15': ("'count': len(active)", "'count': len(entries)"),
    'M16': ("            by_category[item['category']] = by_category.get(item['category'], 0) + item['cents']",
            "            category = active[0]['category']\n            by_category[category] = by_category.get(category, 0) + item['cents']"),
    'M17': ("if not args.title.strip() or not args.category.strip() or args.cents <= 0:",
            "if not args.category.strip() or args.cents <= 0:"),
    'M18': ("if not args.title.strip() or not args.category.strip() or args.cents <= 0:",
            "if not args.title.strip() or args.cents <= 0:"),
    'M19': ("            print('unknown expense id', file=sys.stderr)\n            return 1",
            "            print('null')\n            return 0"),
    'M20': ("    return json.loads(state.read_text()) if state.exists() else []",
            "    return json.loads(state.read_text())"),
    'M21': ("    state.parent.mkdir(parents=True, exist_ok=True)", "    pass  # omit parent creation"),
    'M22': ("    print(json.dumps(result, ensure_ascii=False))",
            "    print('INFO: command completed')\n    print(json.dumps(result, ensure_ascii=False))"),
}

EQUIVALENT = (
    "    state.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\\n')",
    "    state.write_text(json.dumps(entries, ensure_ascii=False, indent=4) + '\\n')")


def apply(source, mutation):
    old, new = mutation
    if source.count(old) != 1:
        raise ValueError('Expected exactly one mutation location')
    return source.replace(old, new)
