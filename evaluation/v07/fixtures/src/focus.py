def pick_next(rows, cursor):
    undone = [row for row in rows if not row.get('done')]
    if not undone:
        return None
    unpinned = [row for row in undone if not row.get('pin')]
    if not unpinned:
        return min(undone, key=lambda row: row['id'])
    ordered = sorted(unpinned, key=lambda row: row['id'])
    later = [row for row in ordered if cursor is not None and row['id'] > cursor]
    return later[0] if later else ordered[0]
