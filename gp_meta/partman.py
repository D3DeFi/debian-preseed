import config as c
from collections import OrderedDict


def make_partitions():
    raid_conf = ''
    partman_conf = ''
    if c.PT_METHOD == 'raid':
        name = 'multiraid :: '
        raid_conf += '4096 5000 -1 raid $lvmignore{ } method{ raid } . '
    else:
        name = 'custom :: '

    partman_conf += name + raid_conf
    for part_name, part_args in c.PT_LVM_PARTITIONS.iteritems():
        line = '%d %d %d %s $defaultignore{ } $lvmok{ } method{ %s } format{ } ' % (
                part_args[0], part_args[0] + 1, part_args[1], part_args[2],
                'swap' if part_args[2] == 'linux-swap' else 'format'
        )
        if part_args[2] != 'linux-swap':
            line += 'use_filesystem{ } filesystem{ %s } mountpoint{ %s } . ' % (
                    part_args[2], part_args[3]
            )
        else:
            line += '. '

        partman_conf += line

    return partman_conf


def make_raid():
    partman_conf = '{0} {1} {2} {3} {4} {5} .'.format(
            c.PT_RAID_TYPE, c.PT_RAID_DISK_NUM, 0, c.PT_RAID_FS_ON_TOP, c.PT_RAID_FS_MNTPNT,
            ''.join([disk + '1#' for disk in c.PT_USE_DISKS.split()]).rstrip('#')
    )
    return partman_conf


def partition():
    final_conf = ''
    for key, prompt in PT_PROMPTS.iteritems():
        if key == 'part_recipe_raid':
            if c.PT_METHOD == 'raid':
                final_conf += prompt + '\n'
            else:
                continue
        else:
            final_conf += prompt + '\n'

    for confirm in PT_CONFIRMATIONS:
        final_conf += confirm + '\n'

    return final_conf


def partition_dry_run(free_space):
    names, minimum, maximum, priority = [], [], [], []
    free_space = float(free_space)
    for index, dict_item in enumerate(c.PT_LVM_PARTITIONS.iteritems()):
        key, value = dict_item
        names.append(key)
        minimum.append(value[0])
        priority.append(value[0] + 1)
        if value[1] == -1:
            maximum.append(1000000)
        else:
            maximum.append(value[1])

    factor = []
    for i, name in enumerate(names):
       factor.append(priority[i] - minimum[i])

    ready = False
    while not ready:
        minsum = sum(minimum)
        factsum = sum(factor)
        ready = True
        for i, name in enumerate(names):
            x = minimum[i] + (free_space - minsum) * factor[i] / factsum
            if x > maximum[i]:
                x = maximum[i]
            if x != minimum[i]:
                ready = False
                minimum[i] = x

    output = ''
    for size, name in zip(minimum, names):
        output += '{} => {}MB\n'.format(name, abs(size))

    return output
        

PT_PROMPTS = OrderedDict([
    ('part_method', 'd-i partman-auto/method string {}'.format(c.PT_METHOD)),
    ('part_disk', 'd-i partman-auto/disk string {}'.format(c.PT_USE_DISKS)),
    ('vg_name', 'd-i partman-auto-lvm/new_vg_name string {}'.format(c.PT_LVM_VG_NAME)),
    ('boot_lvm', 'd-i partman-auto-lvm/no_boot boolean {}'.format(c.PT_LVM_BOOT)),
    ('part_recipe_raid', 'd-i partman-auto-raid/recipe string {}'.format(make_raid())),
    ('part_recipe', 'd-i partman-auto/expert_recipe string {}'.format(make_partitions())),
])

PT_CONFIRMATIONS = [
    'd-i partman-lvm/device_remove_lvm boolean true',
    'd-i partman-md/device_remove_md boolean true',
    'd-i partman-lvm/confirm boolean true',
    'd-i partman-lvm/confirm_nooverwrite boolean true',
    'd-i partman-partitioning/confirm_write_new_label boolean true',
    'd-i partman/choose_partition select finish',
    'd-i partman/confirm boolean true',
    'd-i partman/confirm_nooverwrite boolean true',
    'd-i partman-md/confirm boolean true',
    'd-i partman-md/confirm_nooverwrite boolean true',
]
