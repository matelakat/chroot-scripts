import sys
import collections
import subprocess


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


def debootstrap(tgt_dir, mirror):
    proc = subprocess.Popen([
        'sudo', 'debootstrap', '--arch=amd64', '--components=main,universe',
        '--include=language-pack-en', 'precise', tgt_dir, mirror],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return ProcResult(returncode=proc.returncode, out=out, err=err)


def dump(chroot, dump_file):
    with open(dump_file, 'wb') as dump:
        proc = subprocess.Popen([
            'sudo', 'chroot', chroot, 'tar',
            '-czf', '-', '/'],
            stdout=dump, stderr=subprocess.PIPE)
        out, err = proc.communicate()
    return ProcResult(returncode=proc.returncode, out=out, err=err)
