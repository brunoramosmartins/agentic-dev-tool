# Skills

Skills are structured Markdown documents that define LLM system prompts
for specialized behaviors (e.g., supervised engineering guidance).

## Built-in skills

### Supervised Engineering

Located at `src/adt/skills/supervised_engineering/SKILL.md`.

This skill powers the `--mode supervised` workflow. It instructs the LLM
to break problems into steps, provide hints rather than solutions, and
adjust guidance based on the difficulty level.

## Skill loading

Skills are loaded via `load_skill_context()` which returns a
`SkillContext` Pydantic model:

```python
from adt.skills.context import SkillContext

class SkillContext(BaseModel):
    name: str
    markdown: str
    variables: dict[str, str] = {}
    version: str = "0"
```

The version is parsed from a `<!-- version: N -->` HTML comment
in the Markdown header.

## Community skills

Place custom skills under `~/.adt/plugins/skills/<name>/SKILL.md`.
See the [Plugins guide](../guides/plugins.md) for details.
