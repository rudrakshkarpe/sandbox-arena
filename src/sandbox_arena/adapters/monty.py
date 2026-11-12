"""Monty interpreter-tier adapter.

``MontyProvider`` already implements the playground ``Provider`` protocol. It also
declares the interpreter-tier capabilities so the registry can route packs to it.
"""

from ..playground_runner import MontyProvider

MontyAdapter = MontyProvider

__all__ = ['MontyAdapter']
