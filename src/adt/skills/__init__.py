"""Reusable, versionable skill definitions consumed by agents and supervisors.

A *skill* is a self-contained directory with a ``SKILL.md`` document and an
optional Python loader. Skills encode behavior heuristics that the core code
references at runtime, so they can be edited independently of the agent
implementations and shipped with the package as data files.
"""
