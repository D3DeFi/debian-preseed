# debian-preseed
This repository contains tools for automatic generation of a Debian's preseed file and its implementation into Debian Linux
ISO image of version 7 and higher. Currently, there are two scripts, debian-preseed.sh and generate_preseed.py, handling above
mentioned actions.

**debian-preseed.sh** is a bash script, which attaches specified preseed file into ISO's initrd.gz archive, providing way to choose
'autoinstall' as a method during Debian installation. Usage is as follows:
<pre>./debian-preseed.sh SOURCE_ISO PRESEED_FILE</pre>

**preseed.py** is a Python script for automatic generation of a preseed file. File is generated based on options located in .ini file 
and preseed template file. To generate preseed, fill options in config.ini file first and then run following command:

<pre>python2 preseed.py -o preseed.cfg</pre>

For more help on how to use preseed.py file, simply run:

<pre>python2 preseed.py -h</pre>
