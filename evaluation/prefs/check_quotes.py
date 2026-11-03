#!/usr/bin/env python3
"""Report quotes in an analysis that do not appear verbatim in its source slice."""
import re
import sys

source, analysis = (open(p).read() for p in sys.argv[1:3])
norm = lambda s: re.sub(r"\s+|[‘’'\"“”]", '', s)
haystack = norm(source)
quotes = re.findall(r'「([^」]{4,300})」', analysis)
missing = [q for q in quotes if not all(p in haystack for p in re.split(r'……|…', norm(q)) if len(p) >= 4)]
print(f'{len(quotes)} quotes, {len(missing)} not found verbatim')
for q in missing:
    print('  ', q[:80])
