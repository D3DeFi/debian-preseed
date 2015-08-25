#!/bin/sh

# When this script is run, there are 2 active systems which are installed and installation systems
# installed system can be found in /target directory

# This lv is created during preseed installation as a placeholder.
# By default, partman uses all space in VG and assigns it to the last lv defined.
# Motivation is that we want some space left unallocated for future needs
PLACEHOLDER_LV=todelete

for vg in `vgdisplay -c | cut -d: -f1`
 do
	if lvdisplay /dev/${vg}/${PLACEHOLDER_LV} 2>/dev/null
	 then
		lvremove -f /dev/${vg}/${PLACEHOLDER_LV}
	fi
done	
