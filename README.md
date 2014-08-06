chroot-scripts
==============

    mkdir example
    sudo python chroot-create.py example \
        http://www.mirrorservice.org/sites/archive.ubuntu.com/ubuntu/

    sudo python chroot-dump.py example/ exampledump.tgz

    sudo python chroot-setup.py example

    sudo python chroot-enter.py example
