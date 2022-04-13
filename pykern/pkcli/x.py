import argh
import argparse


def run_internal():
    """This is the subject line

        this is some extra stuff

        Args:
            these are the args
    """
    prog = 'prog' + ' ' + 'module'

    parser = argparse.ArgumentParser(
            prog=prog, formatter_class=argh.PARSER_FORMATTER)

    res = argh.dispatch(parser, argv=['module', '-h'])


