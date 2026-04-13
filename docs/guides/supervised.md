# Supervised Learning Mode

The supervised mode guides you step-by-step through solving a programming
problem instead of giving you the answer directly.

## Usage

```bash
adt ask "Implement a linked list" --mode supervised --level beginner
```

## Difficulty levels

| Level | Description |
|-------|-------------|
| `beginner` | Detailed guidance, more hints, smaller steps |
| `intermediate` | Balanced hints, standard step size |
| `advanced` | Minimal hints, larger conceptual steps |

## Sessions

Supervised mode persists state between CLI invocations so you can
continue where you left off:

```bash
adt session show                   # current session state
adt session list                   # all named sessions
adt ask "..." --session algo-practice  # use a named session
adt session clear --yes            # reset
```

## Code review

After implementing a step, submit your code for structured feedback:

```bash
adt review solution.py --level intermediate
```

The reviewer returns issues (with severity and hints), strengths,
improvements, and a verdict (`needs_work`, `on_track`, `excellent`).
