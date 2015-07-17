from collections import OrderedDict

BASE_TEMPLATE = 'gp_meta/preseeds/template.cfg'

DP_NETCFG = 'true' # Enable network configuration. Without this, mirror will fail
DP_DOMAIN = 'DOMAIN' # Domain for server
DP_ROOT_PASS = 'toor' # Temporary root password
DP_TZ = 'UTC' # Timezone specification

# Install software
DP_PACKAGES = 'openssh-server \
build-essential \
nfs-common \
puppet \
ruby \
ruby-dev \
rubygems \
ssh \
ca-certificates \
curl \
linux-headers-amd64 \
vim \
lvm2 \
'

DP_GRUB = '/dev/sda' # Install GRUB to disk

### Partitioning
# Partitionning method (raid, lvm) - Note, that you can use LVM on top of RAID
# by specifiing method as a 'raid' and latter desciribng partitions as LVM
PT_METHOD = 'raid'

# Disks to be used in raid and partitioning. Debian's partman can only work with specified 
# disks. There is currently no way to work with disks separately.
PT_USE_DISKS = '/dev/sda /dev/sdb /dev/sdc /dev/sdd'

## RAID
PT_RAID_TYPE = '10' # supported raids by this script: 0, 1, 10
PT_RAID_DISK_NUM = '4' # must match PT_USE_DISKS number
PT_RAID_FS_ON_TOP = 'lvm' # lvm, ext3 ..
PT_RAID_FS_MNTPNT = '-' # - = none, /, /tmp ...

## LVM
PT_LVM_BOOT = 'true' # It's ok to have /boot partition on LVM
PT_LVM_VG_NAME = 'data' # Volume group name

# Partitions to create. Parameters are as follows: [min_size, max_size, fs, mountpoint]
# Note: 1 in max_size means to use rest of the unnallocated space
# I really recommend for all but last partition to have min_size and max_size same
PT_LVM_PARTITIONS = OrderedDict([
   ('root', [4096, 4096, 'ext3', '/']),
   ('swap', [1024, 1024, 'linux-swap', '']),
   ('var', [6100, 6100, 'ext3', '/var']),
   ('home', [4096, -1, 'ext3', '/home']),
])
