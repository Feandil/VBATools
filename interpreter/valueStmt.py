from .base import register, register_as, go_through, Base, NotResolvable
from .literals import Number, Literal

def captureValueError(func):
    def wrapped(*args, **xargs):
        try:
            return func(*args, **xargs)
        except ValueError:
            raise NotResolvable()
    return wrapped

@captureValueError
def add(x, y):
    if isinstance(x, Number):
        if isinstance(y, Number):
            return Number(x.value + y.value)
        else:
            return Number(x.value + int(y.value))
    elif isinstance(y, Number):
        return Number(int(x.value) + y.value)
    return Literal(x + y)


BinaryOperators = {
    "'+'": add,
    "'*'": captureValueError(lambda x,y: Number(int(x.value) * int(y.value))),
    "'-'": captureValueError(lambda x,y: Number(int(x.value) - int(y.value))),
}

@register
class valueStmt(Base):
    @classmethod
    def parse(cls, node):
        vSt = cls(node)
        print vSt
        children = vSt.children
        try:
            if len(children) == 1:
                # vsLiteral, vsICS, vsTypeOf or vsMid
                return children[0].resolve()
            if len(children) == 2:
                # vsNew, vsAddressOf, vsNegation, vsPlus or vsNot
                pass
            if hasattr(children[0], 'name') and children[0].name == "'('":
                # vsStruct
                children = [child.resolve() for child in children[1::2]]
                if len(children) == 1:
                    return children[0]
            # Binary operators
            (x, y) = (children[0].resolve(), children[2].resolve())
            try:
                return BinaryOperators[children[1].name](x,y)
            except KeyError:
                pass
        except NotResolvable:
            pass
        return vSt
