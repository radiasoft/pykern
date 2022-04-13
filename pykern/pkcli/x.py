import argh
import argparse


def run_internal():
    """This is the subject line for run_internal

        this is some extra stuff

        Args:
            these are the args
    """
    prog = 'prog' + ' ' + 'module'

    parser = argparse.ArgumentParser(
            prog=prog, formatter_class=argh.PARSER_FORMATTER)

    res = argh.dispatch(parser, argv=['module', '-h'])

def foo():
    """This is the subject line for foo

        this is something we dont need

        Args:
            arg1
            arg2
    """
    return True
