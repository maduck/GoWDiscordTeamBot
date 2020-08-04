import re

def atoi(text):
    return int(text) if text.isdigit() else text

def format_bool(value):
    return "✅" if value else "❌"

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    if type(text) in [tuple, list]:
        # List.
        return [ atoi(c) for c in re.split(r'(\d+)', text[0]) ]
    else:
        # String or bytes.
        return [ atoi(c) for c in re.split(r'(\d+)', text) ]

# https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries
def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                # Use a for conflicts.
                pass
                # raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            print(f"FILL: {key} : {b[key]}")
            a[key] = b[key]
    return a