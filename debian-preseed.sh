#!/bin/bash
# This script currently support only 64bit installation iso images
# Recommended is to use debian 7 wheezy

LOOPDIR='./loopdir'
IRMOD='./irmod'
CDRW='./cd'
ISO='debian-preseed.iso'

if [ $# -ne 2 ]; then
    echo "Usage: $0 <source_iso> <preseed_file>"
    exit 1
fi

if [ $EUID -ne 0 ]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

rm -rf $CDRW $IRMOD
mkdir -p $LOOPDIR
mkdir -p $CDRW
mkdir -p $IRMOD

ISO_SRC=$1 	# save first argument to ISO_SRC
PRESEED_FILE=$2 	# 	and second argument to PRESEED_FILE
CFG=$CDRW/isolinux/txt.cfg
ISO_LABEL=`blkid -o value $ISO_SRC | awk 'NR == 1'`


echo "== mounting $ISO_SRC"
mount -o loop $ISO_SRC $LOOPDIR

echo "== copying data from $ISO_SRC"
rsync -a -H --exclude=TRANS.TBL $LOOPDIR/ $CDRW

echo "== umounting $ISO_SRC"
umount $LOOPDIR

echo "== extracting initrd.gz"
cd irmod && gzip -d < ../cd/install.amd/initrd.gz | cpio --extract --make-directories --no-absolute-filenames

echo "== copying $PRESEED_FILE to right place :)"
cp ../$PRESEED_FILE preseed.cfg
cp ../postinst.sh bin/postinst.sh

echo "== create new initrd.gz"
find . | cpio -H newc --create | gzip -9 > ../cd/install.amd/initrd.gz

echo "== removing $IRMOD"
cd ../
rm -fr irmod/

echo "== editing $CFG"
cat << EOF > $CFG
default install
label install
        menu label ^AutoInstall 
        menu default
        kernel /install.amd/vmlinuz
        append file=/preseed.cfg vga=788 initrd=/install.amd/initrd.gz -- quiet 
EOF

echo "== fixing MD5"
cd $CDRW
md5sum $(find -type f ! -name "md5sum.txt" ! -path "./isolinux/*" ! -name "debian") > md5sum.txt
cd ..

echo "== generating new iso image: $ISO"
genisoimage -o $ISO -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -R -J -V "$ISO_LABEL" -T -quiet $CDRW

echo "== cleaning up"
rm -rf $CDRW $IRMOD $LOOPDIR
