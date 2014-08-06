import argparse
import os
import sys
import chroot_lib


def get_args_or_die(args):
    parser = argparse.ArgumentParser(description="Setup a chroot")
    parser.add_argument('target_directory', help="target directory")
    return parser.parse_args(args)


def check_args(args):
    target_directory = os.path.normpath(os.path.abspath(args.target_directory))
    if not os.path.exists(target_directory):
        raise SystemExit(target_directory + " does not exist")
    if not os.path.isdir(target_directory):
        raise SystemExit(target_directory + " is not a directory")
    result = argparse.Namespace(target_directory=target_directory)
    return result


def main():
    args = check_args(get_args_or_die(sys.argv[1:]))

    chroot_lib.enter(args.target_directory)


if __name__ == "__main__":
    main()
