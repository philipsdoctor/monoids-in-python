# infix hack
class Infix(object):
    def __init__(self, func):
        self.func = func

    def __or__(self, other):
        return self.func(other)

    def __ror__(self, other):
        from functools import partial
        return Infix(partial(self.func, other))

    def __call__(self, v1, v2):
        return self.func(v1, v2)



# Parsing

# Consider the following grammar (written in BNF notation):
# expr ::= factor + expr | factor - expr | factor
# factor ::=  term * factor | term / factor | term
# term ::=  variable | number | (expr)

# When writing compilers or interpreters, one approach is to begin with:
# "x * (x + 1) / (2 - y)"

# And convert it to an *Abstract Syntax Tree* (AST):

# {'Op': '*',
#  'a': {'Op': 'variable', 'name': 'x'},
#  'b': {'Op': '/',
#        'a': {'Op': '+',
#              'a': {'Op': 'variable', 'name': 'x'},
#              'b': {'Op': 'number', 'value': 1.0}},
#        'b': {'Op': '-',
#              'a': {'Op': 'number', 'value': 2.0},
#              'b': {'Op': 'variable', 'name': 'y'}}}}

# Once you have an AST, programming rules for compiling/interpreting
# is called *semantics*

# First step: tokenize
def tokenize(str):
    "Takes a string and outputs a list of 'tokens', or small strings used by the parser"
    import re
    return re.findall("\d+\.?\d*|\w+|\+|\-|\(|\)|\*|/", str)

# As an aside, regular expressions have a monoid structure too, `|` is (x) and `[^.]` is 0

# Here are a few example parsers.
# They take tuples (tokenList, resultObject) and return (tokenList, resultObject)
def anyString(t):
    "Parse any string"
    tl, _ = t
    return tl[1:], tl[0]

def anyFloat(t):
    "Parse any float"
    tl, _ = t
    try: return tl[1:], float(tl[0])
    except: return tl, None

def string(s):
    "Takes a string and returns a parser for that string"
    def p(t):
        tl, _ = t
        if len(tl) > 0 and tl[0] == s: return tl[1:], s
        else : return tl, None
    return p

# For convenience, we sometimes want to trivial parsers that don't
# actually try to parse anything, but do return particular objects

def returnResult(obj):
    "Makes a parser which has obj as a result"
    def p(t):
        tl, _ = t
        return tl, obj
    return p

# A convenient trivial parser: the "failing" parser
fail = returnResult(None)

# A parsing *combinator* is a higher order function
# It takes two parsers and returns a parser

# Here's some parsing combinators

@Infix
def dropThen(p1,p2):
    """Apply the first parser and if it's successful, drop its result,
    then apply the other parser and keep that result.
    If either parser fails, rewind the tokens and make the result None"""
    def p(t):
        tl1, r1 = p1(t)
        if r1 != None:
            tl2, r2 = p2((tl1, r1))
            if r2 != None: return tl2, r2
        tl0, _ = t
        return tl0, None
    return p

@Infix
def thenDrop(p1,p2):
    """Apply the first parser and if it's successful, keep its result,
    then apply the other parser and drop that result.
    If either parser fails, rewind the tokens and make the result None"""
    def p(t):
        tl1, r1 = p1(t)
        if r1 == None: return fail(t)
        tl2, r2 = p2((tl1, r1))
        if r2 == None: return fail(t)
        return tl2, r1
    return p

@Infix
def l(p1,p2):
    """Try one parser if that fails, try the second"""
    def p(t):
        tl1, r1 = p1(t)
        if r1 != None: return tl1, r1
        return p2(t)
    return p

# Monoids in Parsing

# Parsers we've described form a monoid:
# `|l|` is (x) and `fail` is 0

x = anyFloat
y = anyString
z = string('+')

zero = fail

t = (tokenize('123 + abc'),None)

assert (x |l| zero)(t) == (zero |l| x)(t) == x(t)
assert ((x |l| y) |l| z)(t) == (x |l| (y |l| z))(t)

# Putting it all together, let's generate some parsers according to our grammar.

# First, since it's convenient to write a little combinator specific to our AST:
def op(o):
    """Takes an operator o and returns an (infix) combinator which
    parses two things and makes an AST with the results and o as the operator"""
    @Infix
    def p0(p1,p2):
        def p(t):
            tl1, r1 = (p1 |thenDrop| string(o))(t)
            if r1 == None: return fail(t)
            tl2, r2 = p2((tl1, r1))
            if r2 == None: return fail(t)
            return tl2, {'Op': o, 'a': r1, 'b': r2}
        return p
    return p0

# Writing the parser is almost trivial now... just follow the BNF grammar
def expr(t):
    "expr ::= factor + expr | factor - expr | factor"
    return ((factor |op('+')| expr) |l| (factor |op('-')| expr) |l| factor)(t)

def factor(t):
    "factor ::=  term * factor | term / factor | term"
    return ((term |op('*')| factor) |l| (term |op('/')| factor) |l| term)(t)

def term(t):
    "term ::=  variable | number | (expr)"
    return (number |l| variable |l| (string('(') |dropThen| expr |thenDrop| string(')')))(t)

def variable(t):
    "Parses a variable to an AST"
    tl, r = anyString(t)
    if r == None or r in "()": return fail(t)
    return tl, {'Op': 'variable', 'name': r}

def number(t):
    "Parses a number to an AST"
    tl, r = anyFloat(t)
    if r == None: return fail(t)
    return tl, {'Op': 'number', 'value': r}

def parse(p,s):
    "Runs a parse on a string, returning the result"
    return p((tokenize(s),None))[1]

from pprint import pprint
pprint(parse(expr,"x * (x + 1) / (2 - y)"))