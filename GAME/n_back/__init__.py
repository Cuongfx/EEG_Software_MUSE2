__all__ = ["run"]


def run() -> None:
    from .main import run as run_main

    run_main()
