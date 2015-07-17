#!/usr/bin/python2.7

import sys
import argparse
from gp_meta import config, partman
import subprocess
import re


def output_preseed_file(output_file=None):
    final_preseed = ''
    try:
        with open(config.BASE_TEMPLATE, 'r') as template:
            for line in template:
                if re.search('DP_.*$', line) is not None:
                    if line.endswith('DP_PARTITION\n'):
                        final_preseed += partman.partition()
                    else:
                        config_item = line.split()[-1].rstrip()
                        replacement = getattr(config, config_item)
                        final_preseed += line.replace(config_item, replacement)
                else:
                    final_preseed += line
    except IOError:
        print('Base template not found in {}'.format(config.BASE_TEMPLATE))
        sys.exit(1)

    if output_file is not None:
        try:
            with open(output_file, 'w') as output:
                output.write(final_preseed)
        except IOError:
            print('Unable to write to {}'.format(output_file))
            sys.exit(1)

    return final_preseed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-n', '--dry-run', action='store', dest='total_space_mb', 
            help='outputs size of each partition as they will be after installation. TOTAL_SPACE_MB expects free size to be partitioned'
    )
    parser.add_argument(
            '-o', '--output-file', action='store', dest='output_file', 
            help='output file to write preseed configuration to'
    )
    parser.add_argument(
            '--gen-iso', action='store', dest='input_iso',
            help='automatically run debian-preseed.sh to generate iso with preseed configuration. INPUT_ISO specifies clean debian iso to be enhanced with preseed'
    )
    parser.add_argument('-q', '--quiet', action='store_true', default=None, help='silent mode')
    args = parser.parse_args()

    if args.total_space_mb:
        print partman.partition_dry_run(args.total_space_mb)

    if args.input_iso:
        if args.output_file:
            output_preseed_file(output_file=args.output_file)
            if args.quiet:
                devnull = open('/dev/null', 'w')
                subprocess.call(['./debian-preseed.sh', args.input_iso, args.output_file], stdout=devnull)
            else:
                subprocess.call(['./debian-preseed.sh', args.input_iso, args.output_file], stdout=None)
        else:
            print('Required parameter -o missing. Run program with --gen-iso input_iso -o file.')
            sys.exit(1)

    if args.output_file:
        output_preseed_file(output_file=args.output_file)
    else:
        print output_preseed_file()
