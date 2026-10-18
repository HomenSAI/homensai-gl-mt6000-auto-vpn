"""Which statistics a Telegram report contains. The owner chooses them with check boxes; the header, the report id and a controller ALARM line are always sent."""
ITEMS = ('servers', 'events', 'traffic', 'delta', 'controller', 'controller_events', 'controller_totals', 'gaps')
PRESETS = {'minimum': ('servers',),
           'standard': ('servers', 'events', 'traffic', 'controller'),
           'maximum': ITEMS}


def parse(value):
    """Stored option -> tuple of item ids. Unset or empty means everything (the behaviour before the choice existed); 'none' means nothing."""
    if value is None or value == '':
        return ITEMS
    if value == 'none':
        return ()
    if not isinstance(value, str):
        return ITEMS
    chosen = {part for part in value.split(',') if part in ITEMS}
    return tuple(item for item in ITEMS if item in chosen)


def encode(items):
    """List of ids from the page -> stored option; refuses anything unknown."""
    if not isinstance(items, str) or len(items) > 200:
        raise ValueError('TELEGRAM-ITEMS')
    if items == 'none':
        return 'none'
    parts = items.split(',')
    if not parts or any(part not in ITEMS for part in parts) or len(set(parts)) != len(parts):
        raise ValueError('TELEGRAM-ITEMS')
    return ','.join(item for item in ITEMS if item in parts)
