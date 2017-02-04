KNOWN_VBA = {}

def register(cls):
    KNOWN_VBA[cls.__name__] = cls
    return cls

def register_as(cls, name):
    KNOWN_VBA[name] = cls

IGNORED_VBA = set(['WS'])
PASS_THROUGH = set()

def ignore(name):
    IGNORED_VBA.add(name)

def go_through(name):
    PASS_THROUGH.add(name)

def parse(node):
    name = node['name']
    if name in IGNORED_VBA:
        return None
    if name in PASS_THROUGH:
        return parse(node['children'][0])
    try:
        return KNOWN_VBA[name].parse(node)
    except KeyError:
        return Base(node)

class NotResolvable(Exception):
    pass

class Base(object):
    def __init__(self, node):
        self.name = node['name']
        if 'children' in node:
            children = (parse(child) for child in node['children'])
            children = [child for child in children if child is not None]
            if children:
                self.children = children
        if 'value' in node:
            self.value = node['value']

    @classmethod
    def parse(cls, node):
        return cls(node)

    def resolve(self):
        raise NotResolvable()

    def __str__(self):
        try:
            return ''.join(str(child) for child in self.children)
        except AttributeError:
            return self.value

