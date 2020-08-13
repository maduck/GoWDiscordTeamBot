import re


def atoi(text):
    return int(text) if text.isdigit() else text


def bool_to_emoticon(value):
    return value and "✅" or "❌"


def natural_keys(text):
    """
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    """
    if type(text) in [tuple, list]:
        return [atoi(c) for c in re.split(r'(\d+)', text[0])]
    return [atoi(c) for c in re.split(r'(\d+)', text)]


# https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries
# merges b into a
def merge(a, b, path=None):
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
        else:
            a[key] = b[key]
    return a


def flatten(*args):
    lst = []
    for arg in args:
        if type(arg) == str and arg != '':
            lst.append(arg)
        elif type(arg) == list:
            lst.extend(arg)
    return lst


async def pluralize_author(author):
    if author[-1] == 's':
        author += "'"
    else:
        author += "'s"
    return author


def chunks(iterable, chunk_size):
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]
