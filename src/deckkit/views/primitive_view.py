from .view import View


class PrimitiveView(View):
    """A rendering leaf supported directly by the resolver and backends.

    Subclassing alone does not register a new primitive with the compiler.
    """
