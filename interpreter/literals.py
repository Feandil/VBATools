from .base import register, register_as, go_through, Base

go_through('literal')

class Literal(Base):
    def __init__(self, value):
        self.value = value
    @classmethod
    def parse(cls, node):
        return cls(node['value'])
    def __str__(self):
        return str(self.value)
    def resolve(self):
        return self

register_as(Literal, 'STRINGLITERAL')

class Number(Literal):
    def __init__(self, value):
        self.value = int(value)

register_as(Number, 'HEXLITERAL')
register_as(Number, 'OCTLITERAL')
register_as(Number, 'INTEGERLITERAL')
register_as(Number, 'SHORTLITERAL')
