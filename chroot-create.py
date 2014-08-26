import argparse
import os
import sys
import chroot_lib


def get_args_or_die(args):
    parser = argparse.ArgumentParser(description="Create a chroot")
    parser.add_argument('target_directory', help="target directory")
    parser.add_argument('mirror', help="ubuntu mirror to use")
    parser.add_argument('--suite', help="ubuntu suite to use",
                        default='precise', choices=['precise', 'trusty'])
    parser.add_argument('--minbase', help="Create a minimal install",
                        default=False, action="store_true")
    return parser.parse_args(args)


def check_args(args):
    target_directory = os.path.normpath(os.path.abspath(args.target_directory))
    if os.path.exists(target_directory):
        raise SystemExit(target_directory + " Already exists")
    result = argparse.Namespace(
        target_directory=target_directory, mirror=args.mirror,
        suite=args.suite, minbase=args.minbase)
    return result


def main():
    args = check_args(get_args_or_die(sys.argv[1:]))

    result = chroot_lib.debootstrap(args.target_directory, args.mirror,
                                    args.suite, args.minbase)
    if result.failed:
        result.die()


if __name__ == "__main__":
    main()
