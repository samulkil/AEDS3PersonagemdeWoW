import tokenize, io, re, sys

def strip_comments(source: str) -> str:
    tokens = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type != tokenize.COMMENT:
                tokens.append(tok)
    except tokenize.TokenError:
        return source
    out = tokenize.untokenize(tokens)
    out = re.sub(r'[ \t]+\n', '\n', out)
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out

for path in sys.argv[1:]:
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    out = strip_comments(src)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(out)
    print(f"Cleaned: {path}")
