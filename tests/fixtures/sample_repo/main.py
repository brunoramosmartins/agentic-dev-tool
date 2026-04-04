"""Minimal entry point for fixture repository."""


def main() -> None:
    print(greet("adt"))


def greet(name: str) -> str:
    return f"hello {name}"


if __name__ == "__main__":
    main()
