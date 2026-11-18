"""

Shell DSL entry points and implementation modules.

"""

from __future__ import annotations

from corio.shell.dsl.args import arg, val
from corio.shell.dsl.expression import Expression

ex = Expression.build
shell = ex
