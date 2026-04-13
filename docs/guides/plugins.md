# Plugins

Extend `adt` with community skills and tools without forking the repo.

## Directory layout

```
~/.adt/plugins/
    skills/
        my_skill/
            SKILL.md          # Loaded as SkillContext
    tools/
        my_tool/
            tool.py           # Must define register(registry)
            manifest.json     # Optional metadata
```

## Creating a skill plugin

Create a `SKILL.md` with a version comment:

```markdown
<!-- version: 1 -->
# My Custom Skill

Your skill content here...
```

## Creating a tool plugin

Create a `tool.py` with a `register` function:

```python
from adt.mcp.registry import ToolDefinition

def register(registry):
    registry.register(ToolDefinition(
        name="my_tool",
        description="Does something useful",
        parameters={"type": "object", "properties": {}},
        allowed_agents=["repo_agent"],
        handler=lambda: "result",
    ))
```

## Managing plugins

```bash
adt plugins list              # show installed plugins
adt plugins validate ./path   # check a plugin directory
```

## Safety

Plugin tools are registered through the same `ToolRegistry` and validated
by the same `ExecutionController` as built-in tools. JSON Schema validation
applies to all tool arguments.
