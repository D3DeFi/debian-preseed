# debian-preseed
This repository contains tools for automatic generation of a Debian's preseed file and its implementation into Debian Linux
ISO image of version 7 and higher. Currently, there are two scripts, debian-preseed.sh and generate_preseed.py, handling above
mentioned actions.

**debian-preseed.sh** is a bash script, which attaches specified preseed file into ISO's initrd.gz archive, providing way to choose
'autoinstall' as a method during Debian installation. Usage is as follows:
<pre>./debian-preseed.sh SOURCE_ISO PRESEED_FILE</pre>

**generate_preseed.py** is a python script for automatic generation of a preseed file. This script mainly focuses on a partman's
part of a preseed file, beceause it is the most complicated part of this configuration file. Preseed file is generated based on
input provided by user in a **gp_meta/config.py** file. Use cases are as follows:

For a preview of 'How will be free space divided between partitions' first fillin PT_LVM_PARTITIONS variable in gp_meta/config.py file
and then run:
<pre>./generate_preseed.py -n TOTAL_FREE_SPACE</pre>

For generation of a preseed file, simply run:
<pre>./generate_preseed.py</pre>

If you want to automatically attach generated preseed file into ISO image, run:
<pre>./generate_preseed.py --gen-iso SOURCE_ISO -o OUTPUT_PRESEED</pre>
