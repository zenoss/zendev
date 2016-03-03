import argparse
import ast
import re
import sys
import textwrap


class NodeFinder(object):
    """Locates and returns the immediate child nodes that are of
    a particular type.
    """

    def __init__(self, nodeType, show=False):
        self._type = nodeType
        self._show = show

    def __call__(self, node):

        for n in ast.iter_child_nodes(node):
            if self._show:
                print n
            if isinstance(n, self._type):
                yield n


def isAssignedValue(getter, value, node):
    """Returns True if the attribute value retrieved by getter matches
    value.
    """
    try:
        return getter(node) == value
    except AttributeError:
        return False


def isMethodCall(attrName, methodName, node):
    """Returns True if the node is a methodName invocation on attribute
    attrName.
    """
    if not isinstance(node.value, ast.Call):
        return False
    call = node.value
    if not isinstance(call.func, ast.Attribute):
        return False
    obj = call.func
    if not isinstance(obj.value, ast.Name):
        return False
    return (obj.value.id == attrName and obj.attr == methodName)


class Secured(object):

    def __init__(self, unpublished, private, protected, public):
        self._unpublished = unpublished
        self._private = private
        self._protected = protected
        self._public = public

    @property
    def unpublished(self):
        return self._unpublished

    @property
    def private(self):
        return self._private

    @property
    def protected(self):
        return self._protected

    @property
    def public(self):
        return self._public

    def __len__(self):
        return sum(
            len(self._unpublished),len(self._private),
            len(self._protected), len(self._public)
        )


class Unsecured(object):

    def __init__(self, names):
        self._names = names

    @property
    def names(self):
        return self._names

    def __len__(self):
        return len(self._names)


class AccessInfo(object):

    def __init__(self, name, bases, secured, unsecured):
        self._name = name
        self._bases = bases
        self._secured = secured
        self._unsecured = unsecured

    @property
    def name(self):
        return self._name

    @property
    def bases(self):
        return self._bases

    @property
    def secured(self):
        return self._secured

    @property
    def unsecured(self):
        return self._unsecured


def flattenAttributeTree(node):
    attrSeq = []
    n = node
    while isinstance(n, ast.Attribute):
        attrSeq.insert(0, n.attr)
        n = n.value
    attrSeq.insert(0, n.id)
    return '.'.join(attrSeq)


def _isUnpublishedImplicitely(node):
    """Returns True if the node is a method having the characteristics
    that causes Zope to implicitely _not_ publish it.

    This includes all methods starting with an underscore ('_') or
    lacking a doc-string.
    """
    return node.name.startswith("_") or ast.get_docstring(node) is None


def makeAccessInfo(node):
    bases = []
    for b in node.bases:
        bases.append(flattenAttributeTree(b))

    # Returns all assignment statements within the class def
    # (doesn't include assignments within methods)
    assignments = NodeFinder(ast.Assign)(node)

    # Filter out assignments that aren't an initializer call
    # to the ClassSecurityInfo class.
    security = [
        assign.targets[0].id
        for assign in assignments
        if isAssignedValue(
            lambda x: x.value.func.id, "ClassSecurityInfo", assign
        )
    ]
    if not security:
        raise ValueError("No ClassSecurityInfo class attribute found")

    security = security[0]

    # Sort all the methods into published or unpublished groupings.
    unpublished = set()
    published = set()
    for fn in NodeFinder(ast.FunctionDef)(node):
        if _isUnpublishedImplicitely(fn):
            unpublished.add(fn.name)
        else:
            published.add(fn.name)

    # Identify every method registered as private to the security object.
    private = set()
    protected = set()
    public = set()
    for expr in NodeFinder(ast.Expr)(node):
        if isMethodCall(security, "declarePrivate", expr):
            private.add(expr.value.args[0].s)
        elif isMethodCall(security, "declareProtected", expr):
            protected.add((
            expr.value.args[1].s,
            expr.value.args[0].id
                if isinstance(expr.value.args[0], ast.Name)
                else expr.value.args[0].s
            ))
        elif isMethodCall(security, "declarePublic", expr):
            public.add(expr.value.args[0].s)

    secured = private | set(n for n,_ in protected) | public
    unsecured = published - secured

    return AccessInfo(
        node.name, bases,
        Secured(unpublished, private, protected, public),
        Unsecured(unsecured)
    )


def getTerminalSize():
    import os
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack(
                'hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234')
            )
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        ### Use get(key[, default]) instead of a try/catch
        #try:
        #    cr = (env['LINES'], env['COLUMNS'])
        #except:
        #    cr = (25, 80)
    return int(cr[1]), int(cr[0])


class MyVisitor(ast.NodeVisitor):

    def __init__(self, *args, **kwargs):
        super(MyVisitor, self).__init__(*args, **kwargs)
        self.indent = Indent()

    def visit_ClassDef(self, node):
        print "\n\n%-10s%s%-30s %s" % ("CLASS", self.indent, node.name, node)
        with self.indent as i:
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        print "\n%-10s%s%-30s %s" % ("FUNCTION", self.indent, node.name, node)
        with self.indent as i:
            self.generic_visit(node)

    def visit_Assign(self, node):
        print "%-10s%s%s %s %s" % (
            "ASSIGN", self.indent, node.targets, node.value, node
        )
        #variables = [
        #    n.id for n in node.targets if isinstance(n, ast.Name)
        #]
        with self.indent as i:
            self.generic_visit(node)

    def visit_Call(self, node):
        print "%-10s%s%s %s" % ("CALL", self.indent, node.func, node)
        with self.indent as i:
            self.generic_visit(node)

    def visit_Attribute(self, node):
        print "%-10s%s%s %s %s" % (
            "ATTRIBUTE", self.indent, node.value, node.attr, node.ctx
        )
        with self.indent as i:
            self.generic_visit(node)

    def visit_Name(self, node):
        print "%-10s%s%s %s" % ("NAME", self.indent, node.id, node.ctx)
        with self.indent as i:
            self.generic_visit(node)


class Indent(object):

    def __init__(self):
        self._indent = 0

    def __enter__(self):
        self._indent += 1
        return self

    def __exit__(self, *args):
        self._indent -= 1

    def __eq__(self, value):
        return self._indent == value

    def __str__(self):
        return ' ' * (self._indent * 2)


_reprFunc = {
    ast.Str: lambda x: "'%s'" % x.s,
    ast.Name: lambda x: x.id,
    ast.Call: lambda x: "%s()" % _reprFunc.get(type(x.func))(x.func),
    ast.Attribute: lambda x: "%s.%s" % (_reprFunc.get(type(x.value))(x.value), x.attr)
}

def _repr(node):
    if type(node) in _reprFunc:
        return _reprFunc[type(node)](node)
    return str(node)

width,_ = getTerminalSize()

def printData(label, data, indent=2):
    header = ' ' * indent
    content = ' ' * (indent * 2)
    print header + "%s (%s):" % (label, len(data))
    if len(data):
        print '\n'.join(textwrap.wrap(
            ', '.join(sorted(data)), width=width, break_long_words=False,
            initial_indent=content, subsequent_indent=content
        ))
    else:
        print "%s<No %s methods>" % (content, label)

argParser = argparse.ArgumentParser(
    description="Analyze Python source for missing security declarations"
)
argParser.add_argument("--verbose", action="store_true")
argParser.add_argument(
    "sourcefile", metavar="py", type=str, help="Path to Python source file"
)

if __name__ == "__main__":
    options = argParser.parse_args()

    tree = ast.parse(open(options.sourcefile).read(), '')
    for classNode in NodeFinder(ast.ClassDef)(tree):
        try:
            info = makeAccessInfo(classNode)
        except ValueError:
            if options.verbose:
                print "\nClass %s(%s):" % (
                    classNode.name, ', '.join(n.id for n in classNode.bases)
                )
                print "  <Skipping - no security descriptor>"
            continue

        print "\nClass %s(%s):" % (info.name, ', '.join(info.bases))

        if options.verbose:
            printData("Unpublished", info.secured.unpublished)
            printData("Private", info.secured.private)
            formattedProtected = [
                "%s/%s" % (item[0], item[1]) for item in info.secured.protected
            ]
            printData("Protected", formattedProtected)
            printData("Public", info.secured.public)

        printData("Unsecured", info.unsecured.names)

    #MyVisitor().visit(tree)
    #print "="*80

