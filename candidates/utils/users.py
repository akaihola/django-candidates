import re

from unicodedata import combining, normalize

def noncombining(u):
    return not combining(u)

def remove_diacritics(s, encoding='UTF-8'):
    if isinstance(s, unicode):
        return filter(noncombining, normalize('NFKD', s))
    else:
        return filter(noncombining,
                      normalize('NFKD', s.decode(encoding))).encode(encoding)

def slugify(s):
    return remove_diacritics(s.lower())

def usernameize(s):
    """
    """
    return re.sub(r'\W', '', slugify(s))

def generate_username(first_name, last_name, round_name, n=None):
    """
    Generate a username based on user's first and last names, the name
    of the current round and a counter.  Make sure the length doesn't
    exceed 30 characters.
    """
    if n is None:
        suffix = ''
    else:
        suffix = '_%d' % n
    max_name_len = 30 - len(round_name) - len(suffix)
    name = ('%s%s' % (usernameize(first_name),
                      usernameize(last_name)))[:max_name_len]
    return '%s%s%s' % (name, round_name, suffix)
