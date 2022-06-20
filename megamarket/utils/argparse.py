import os
from typing import Callable
from argparse import ArgumentTypeError


def validate(type: Callable, constrain: Callable):
    def wrapper(value):
        value = type(value)

        if not constrain(value):
            raise ArgumentTypeError
        return value

    return wrapper


positive_int = validate(int, lambda x: x > 0)


def clear_environ(rule: Callable):
    for var in filter(rule, tuple(os.environ)):
        os.environ.pop(var)
