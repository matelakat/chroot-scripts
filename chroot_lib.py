import os
import sys
import collections
import subprocess
import textwrap


ProcResultBase = collections.namedtuple("ProcResultBase", "returncode,out,err")


class ProcResult(ProcResultBase):
    @property
    def failed(self):
        return self.returncode != 0

    def die(self):
        if self.err:
            sys.stderr.write(self.err)
        if self.out:
            sys.stdout.write(self.out)
        sys.exit(1)


class Command(object):
    def __init__(self, args, stdin=None):
        self.args = args
        self.stdin = stdin

    def in_chroot(self, chroot):
        return Command(['chroot', chroot] + self.args, self.stdin)


def debootstrap(tgt_dir, mirror):
    proc = subprocess.Popen([
        'debootstrap', '--arch=amd64', '--components=main,universe',
        '--include=language-pack-en', 'precise', tgt_dir, mirror],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return ProcResult(returncode=proc.returncode, out=out, err=err)


def run_commands_in(chroot, commands):
    chroot_commands = [cmd.in_chroot(chroot) for cmd in commands]
    for result in run_commands(chroot_commands):
        yield result


def run_commands(commands):
    for command in commands:
        proc = subprocess.Popen(command.args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)

        out, err = proc.communicate(command.stdin)
        yield ProcResult(returncode=proc.returncode, out=out, err=err)


def run_till_success(commands):
    for result in run_commands(commands):
        if result.failed:
            return result

    return result


def run_anyway(commands):
    for result in run_commands(commands):
        pass


def setup(chroot):
    policy_file_contents = textwrap.dedent("""
    #!/bin/sh
    exit 101
    """)

    commands = [
        Command(['dd', 'of=/usr/sbin/policy-rc.d'], stdin=policy_file_contents),
        Command(['chmod', 'a+x', '/usr/sbin/policy-rc.d']),
        Command(['dpkg-divert', '--divert', '/usr/bin/ischroot.debianutils',
            '--rename', '/usr/bin/ischroot']),
        Command(['ln', '-s', '/bin/true', '/usr/bin/ischroot'])
    ]

    for result in run_commands_in(chroot, commands):
        if result.failed:
            result.die()


def enter(chroot):
    proc_path = os.path.join(chroot, 'proc')
    sys_path = os.path.join(chroot, 'sys')
    dev_path = os.path.join(chroot, 'dev')
    dev_pts_path = os.path.join(chroot, 'dev', 'pts')

    preparation_commands = [
        Command(['mount', '-t', 'proc', 'proc', proc_path]),
        Command(['mount', '-t', 'sysfs', 'sys', sys_path]),
        Command(['mount', '-o', 'bind', '/dev', dev_path]),
        Command(['mount', '-o', 'bind', '/dev/pts', dev_pts_path]),
    ]
    teardown_commands = [
        Command(['umount', dev_pts_path]),
        Command(['umount', dev_path]),
        Command(['umount', sys_path]),
        Command(['umount', proc_path]),
    ]

    preparation_result = run_till_success(preparation_commands)
    if preparation_result.failed:
        run_anyway(teardown_commands)
        preparation_result.die()
    else:
        commands = [
            Command(['rm', '-f', '/etc/mtab']).in_chroot(chroot),
        ]

        run_till_success(commands)
        proc = subprocess.Popen(['chroot', chroot])
        proc.communicate()
    run_anyway(teardown_commands)


def dump(chroot, dump_file):
    with open(dump_file, 'wb') as dump:
        proc = subprocess.Popen([
            'chroot', chroot, 'tar',
            '-czf', '-', '/'],
            stdout=dump, stderr=subprocess.PIPE)
        out, err = proc.communicate()
    return ProcResult(returncode=proc.returncode, out=out, err=err)
