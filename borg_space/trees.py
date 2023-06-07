# Format a Tree
# Description {{{1
# Given a data hierarchy consisting of zero or more levels of dictionaries with 
# lists as leaf values, where each dictionary key and list value is a string, 
# this function creates a Unicode diagram of that tree.
#
# For example, here is a filesystem sub-hierarchy:
#
#     tests/
#     ├── examples/
#     │   ├── test_example_01.py
#     │   ├── test_example_02.py
#     │   └── test_example_03.py
#     ├── foobar/
#     │   ├── test_foobar_01.py
#     │   ├── test_foobar_02.py
#     │   └── test_foobar_03.py
#     └── hello/
#         └── world/
#             ├── test_world_01.py
#             ├── test_world_02.py
#             └── test_world_03.py

# Imports {{{1
from inform import Info, conjoin, is_collection

def gen_connectors(width):
    space = " "     # This is a non-breaking space, needed with variable width fonts
    line = "─"      # This is horizontal rule
    connector_seeds = dict(
        item = "├",
        last_item = "└",
        lead = "│",
        last_lead = space,
    )
    pad = space if width > 1 else ''

    def extend(seed):
        fill = space if seed in [space, "│"] else line
        return seed + (width - 2)*fill + pad

    return Info(**{k: extend(v) for k, v in connector_seeds.items()})

connectors = gen_connectors(4)

def tree(data, key_suffix=''):
    return _tree(data, key_suffix, top=True)

def _tree(data, key_suffix, top=False, leader=''):
    lines = []
    if hasattr(data, 'items'):
        last = len(data) - 1
        for i, item in enumerate(data.items()):
            key, value = item
            # determine key-leader-supplement and item-leader-supplement
            if top:
                kls = ''
                ils = ''
            elif i < last:
                kls = connectors.item
                ils = connectors.lead
            else:
                kls = connectors.last_item
                ils = connectors.last_lead

            if is_collection(value):
                # append dictionary to those already processed
                lines += [
                    leader + kls + key + key_suffix,
                    _tree(value, key_suffix, leader = leader + ils) if value else None
                ]
            else:
                # the value is a scalar, so squeeze key & value on one line
                lines += [
                    leader + kls + key + ': ' + value,
                ]
        return '\n'.join(l for l in lines if l)

    elif not is_collection(data):
        data = [str(data)]

    if top:
        joiner = '\n'
        terminator = '\n'
        items = conjoin(data, sep='\n', conj='\n')
    else:
        joiner = '\n' + leader + connectors.item
        terminator = '\n' + leader + connectors.last_item
        connector = connectors.item if len(data) > 1 else connectors.last_item
        items = leader + connector + conjoin(data, sep=joiner, conj=terminator)

    if items:
        lines.append(items)
    return '\n'.join(lines)
