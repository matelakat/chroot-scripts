import argparse
import os
import sys
import chroot_lib
import shutil


def get_args_or_die(args):
    parser = argparse.ArgumentParser(description="Backup a chroot")
    parser.add_argument('target_directory', help="target directory")
    parser.add_argument('backup_folder', help="A directory that holds the backup")
    parser.add_argument('--backups_to_keep', help="Number of backups to keep", default="10")
    return parser.parse_args(args)


def assert_existing_dir(path):
    if not os.path.exists(path):
        raise SystemExit(path + " does not exist")
    if not os.path.isdir(path):
        raise SystemExit(path + " is not a directory")


def normalized(path):
    return os.path.normpath(os.path.abspath(path))


def check_args(args):
    target_directory = normalized(os.path.abspath(args.target_directory))
    assert_existing_dir(target_directory)

    backup_folder = normalized(args.backup_folder)
    assert_existing_dir(backup_folder)

    backups_to_keep = int(args.backups_to_keep)

    if backups_to_keep < 1:
        raise SystemExit("backups_to_keep is less than 1")

    result = argparse.Namespace(
        target_directory=target_directory,
        backup_folder=backup_folder,
        backups_to_keep=backups_to_keep)

    return result


def main():
    args = check_args(get_args_or_die(sys.argv[1:]))

    rsync_flags = "-r -h -H -l -g -o -t -D -p --del".split()

    chroot = chroot_lib.Chroot(args.target_directory)

    existing_backups = [
        int(dirname) for dirname in os.listdir(args.backup_folder)]

    def to_path(idx):
        return os.path.join(args.backup_folder, str(idx))


    if existing_backups:
        actual_backup_index = max(existing_backups) + 1
        prev_backup = to_path(actual_backup_index-1)
    else:
        actual_backup_index = 0
        prev_backup = None

    backup_dir = to_path(actual_backup_index)

    chroot.sync_to(backup_dir, prev_backup)

    print "backup at", backup_dir

    indexes_to_remove = sorted(
        existing_backups, reverse=True)[args.backups_to_keep-1:]

    for index in indexes_to_remove:
        path = to_path(index)
        print "removing backup", path
        shutil.rmtree(path)


if __name__ == "__main__":
    main()
