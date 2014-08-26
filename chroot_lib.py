import json
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


def debootstrap(tgt_dir, mirror, suite, minbase):
    minbase_options = ['--variant=minbase'] if minbase else []
    proc = subprocess.Popen([
        'debootstrap', '--arch=amd64', '--components=main,universe',
        '--include=language-pack-en']
        + minbase_options
        + [suite, tgt_dir, mirror],
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

    root = Chroot(chroot)
    hosts = root.get_contents('/etc/hosts')
    hostname = root.get_contents('/etc/hostname').strip()

    for line in hosts.split('\n'):
        if "127.0.1.1" in line:
            if hostname in line:
                break
    else:
        new_hosts_file = "127.0.1.1 {0}\n{1}".format(hostname, hosts)
        root.set_contents('/etc/hosts', new_hosts_file)


    commands = [
        Command(['dd', 'of=/usr/sbin/policy-rc.d'], stdin=policy_file_contents),
        Command(['chmod', 'a+x', '/usr/sbin/policy-rc.d']),
        Command(['dpkg-divert', '--divert', '/usr/bin/ischroot.debianutils',
            '--rename', '/usr/bin/ischroot']),
        Command(['rm', '-f', '/usr/bin/ischroot']),
        Command(['ln', '-s', '/bin/true', '/usr/bin/ischroot'])
    ]

    for result in run_commands_in(chroot, commands):
        if result.failed:
            result.die()


class Chroot(object):
    def __init__(self, root):
        self.root = root
        proc_path = os.path.join(root, 'proc')
        sys_path = os.path.join(root, 'sys')
        dev_path = os.path.join(root, 'dev')
        dev_pts_path = os.path.join(root, 'dev', 'pts')

        self.preparation_commands = [
            Command(['mount', '-t', 'proc', 'proc', proc_path]),
            Command(['mount', '-t', 'sysfs', 'sys', sys_path]),
            Command(['mount', '-o', 'bind', '/dev', dev_path]),
            Command(['mount', '-o', 'bind', '/dev/pts', dev_pts_path]),
            Command(['rm', '-f', '/etc/mtab']).in_chroot(root),
        ]
        self.teardown_commands = [
            Command(['umount', dev_pts_path]),
            Command(['umount', dev_path]),
            Command(['umount', sys_path]),
            Command(['umount', proc_path]),
        ]

    def _fullpath(self, path):
        assert path.startswith('/')
        path = path[1:]
        return os.path.join(self.root, path)

    def sync_to(self, target, link_dest=None):
        rsync_flags = "-r -h -H -l -g -o -t -D -p --del".split()
        exclude_dirs = [
            '/dev/*',
            '/proc/*',
            '/sys/*',
            '/tmp/*',
            '/run/*',
            '/mnt/*',
            '/media/*',
            '/lost+found',
            '/home/*/.gvfs',
        ]
        exclude_args = [
            '--exclude={0}'.format(exclude_dir)
                for exclude_dir in exclude_dirs]

        rsync_flags += exclude_args

        if link_dest:
            rsync_flags += ['--link-dest={0}'.format(link_dest)]

        command = Command([
            'rsync'] + rsync_flags + [self.root + '/', target])

        result = run_till_success([command])
        if result.failed:
            result.die()

    def get_contents(self, path):
        with open(self._fullpath(path), 'rb') as fhandle:
            return fhandle.read()

    def set_contents(self, path, contents):
        with open(self._fullpath(path), 'wb') as fhandle:
            return fhandle.write(contents)

    def prepare(self):
        preparation_result = run_till_success(self.preparation_commands)
        if preparation_result.failed:
            self.teardown()
            preparation_result.die()

    def teardown(self):
        run_anyway(self.teardown_commands)

    @property
    def config(self):
        config_path = os.path.normpath(os.path.abspath(self.root + '.json'))
        if os.path.exists(config_path) and os.path.isfile(config_path):
            with open(config_path, "rb") as config_file:
                data = config_file.read()
            return json.loads(data)
        return {}

    def _to_internal_commands(self, arg_list):
        commands = []
        for args in arg_list:
            commands.append(Command(args).in_chroot(self.root))
        return commands

    def stop(self):
        stop_commands = self._to_internal_commands(
            self.config.get('stop', []))
        run_anyway(stop_commands)
        self.teardown()

    def start(self):
        start_commands = self._to_internal_commands(
            self.config.get('start', []))

        self.prepare()

        start_result = run_till_success(start_commands)
        if start_result.failed:
            self.stop()
            start_result.die()


def enter(chroot, args=[]):
    root = Chroot(chroot)

    root.prepare()

    proc = subprocess.Popen(['chroot', chroot] + args)
    proc.communicate()

    root.teardown()


def dump(chroot, dump_file):
    with open(dump_file, 'wb') as dump:
        proc = subprocess.Popen([
            'chroot', chroot, 'tar',
            '-czf', '-', '/'],
            stdout=dump, stderr=subprocess.PIPE)
        out, err = proc.communicate()
    return ProcResult(returncode=proc.returncode, out=out, err=err)
