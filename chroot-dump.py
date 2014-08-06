import argparse
import os
import sys
import chroot_lib


def get_args_or_die(args):
    parser = argparse.ArgumentParser(description="dump a chroot")
    parser.add_argument('target_directory', help="target directory")
    parser.add_argument('dump_file', help="dump filename")
    return parser.parse_args(args)


def check_args(args):
    target_directory = os.path.normpath(os.path.abspath(args.target_directory))
    dump_file = os.path.normpath(os.path.abspath(args.dump_file))
    if not os.path.exists(target_directory):
        raise SystemExit(target_directory + " does not exists")
    if not os.path.isdir(target_directory):
        raise SystemExit(target_directory + " is not a directory")
    if os.path.exists(dump_file):
        raise SystemExit(dump_file + " already exists")
    result = argparse.Namespace(
        target_directory=target_directory, dump_file=dump_file)
    return result


def main():
    args = check_args(get_args_or_die(sys.argv[1:]))

    result = chroot_lib.dump(args.target_directory, args.dump_file)
    if result.failed:
        result.die()


if __name__ == "__main__":
    main()
