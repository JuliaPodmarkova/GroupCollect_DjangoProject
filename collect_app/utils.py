import re

RU_PROFANITY = [
    r'п(и|е|ы)?з(д|т)',
    r'хуй', r'хую', r'хуя',  r'хуе|ё',
    r'ёб', r'еб[а-я]*',
    r'бля[тд][ьи]?',
    r'сука', r'мудак',
    r'пидор[а-я]*',
    r'гондон[а-я]*',
    r'чмо',
    r'сук(а|и)', r'сучка', r'сучье'
]

PATTERN = re.compile(r'(' + '|'.join(RU_PROFANITY) + r')', flags=re.IGNORECASE)

def censor(text):
    if not isinstance(text, str):
        return text
    return PATTERN.sub('***', text)
