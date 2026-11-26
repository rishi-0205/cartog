"""Check command — argparse dynamic dispatch. PATTERN: CLI-CHECK-01."""
import argparse
from cli.services.check_service import check_service

def build_parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers()
    c = sub.add_parser("check", func=check_service)
    c.set_defaults(func=check_service)
    return p

def run(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)
