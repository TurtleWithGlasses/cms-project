import re
from unidecode import unidecode

def slugify(text):
    text = unidecode(text).lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text
