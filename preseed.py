#!/usr/bin/env python

import sys
from collections import OrderedDict
import ConfigParser
import argparse
import logging


class PreseedCreator(object):
    """PreseedCreator class handles loading of template and configuration files. Based on the 
    mentioned files, PreseedCreator then builds Debian's preseed for ISO images. Preseed 
    files are used during phase of Debian installation to preload installer with 
    already answered questions about system setup."""

    def __init__(self, config_file):
        self.config_file = config_file
        logging.basicConfig(format='%(asctime)-15s %(levelname)s: %(message)s')
        self.logger = logging.getLogger('preseed_output')
        self.logger.setLevel(logging.INFO)
        self.cfparser = ConfigParser.ConfigParser()
        try:
            if self.cfparser.read(self.config_file) == []:
                raise ConfigParser.ParsingError('No config file detected.')
        except ConfigParser.ParsingError:
            self.logger.error('Unable to parse file %s' % self.config_file)
            sys.exit(1)
        self.loaded_template = OrderedDict()
        # special functions are handled by handle_X methods 
        self.special_sections = ['network', 'mirrors', 'partitioning']

    def read_template(self, template):
        """Method read_template loads preseed template file into ordered dictionary for later processing."""
        current_section = None
        try:
            with open(template, 'r') as input_template:
                for line in input_template:
                    if line.startswith('###'):
                        current_section = line.split()[-1]
                        self.loaded_template[current_section] = []
                    elif not line.strip() or line.startswith('#'):
                        continue
                    else:
                        self.loaded_template[current_section].append(line)
        except IOError:
            self.logger.error('No such file %s' % template)
            sys.exit(1)

    def option_lookup(self, section, option):
        """Method option_lookup wraps ConfigParser.get method and adds error handling and logging."""
        try:
            return self.cfparser.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            self.logger.info('%s option was not found predefined in %s, skipping.' % (option, self.config_file))
            return None 

    def create_preseed(self, output_file=None):
        """Method create_preseed builds preseed configuration based on previously loaded template 
        file and options defined in INI configuration file."""
        if not self.loaded_template:
            self.logger.error('No template was preloaded.')
            sys.exit(2)

        preseed_output = ''
        for section in self.cfparser.sections():
            if section in self.special_sections:
                handle_function = getattr(self, 'handle_%s' % section, False)
                if handle_function:
                    preseed_output += handle_function(section)
                else:
                    self.logger.warning('No handler found for section %s, skipping.' % section)
            else:
                template_lines = self.loaded_template.get(section, False)
                if template_lines:
                    for line in template_lines:
                        line_lw = line.split()[-1]
                        if not line_lw.isupper():
                            preseed_output += ''.join(line)
                        else:
                            option = self.option_lookup(section, line_lw.lower())
                            if option is not None:
                                preseed_output += ''.join(line).replace(line_lw, option)

        if output_file is not None:
            with open(output_file, 'w') as out_f:
                out_f.write(preseed_output)
            return
        else:
            return preseed_output

    def handle_network(self, section='network'):
        """Method handle_network applies specific parsing for networking section in preseed template file."""
        network_output = ''
        configure_networking = self.option_lookup(section, 'configure_networking')
        disable_autoconfig = self.option_lookup(section, 'disable_autoconfig')
        template_lines = self.loaded_template.get(section, False)
        if template_lines:
            for line in template_lines:
                line_lw = line.split()[-1]
                if not line_lw.isupper():
                    network_output += ''.join(line)
                    continue
                if line_lw.lower() == 'configure_networking':
                    network_output += ''.join(line).replace(line_lw, configure_networking)
                    if configure_networking == 'false':
                        return network_output
                    continue
                if line_lw.lower() == 'disable_autoconfig':
                    network_output += ''.join(line).replace(line_lw, disable_autoconfig)
                    if disable_autoconfig == 'false':
                        return network_output
                    else:
                        network_output += 'd-i netcfg/dhcp_failed note\n'
                        network_output += 'd-i netcfg/dhcp_options select Configure network manually\n'
                    continue
                        
                option = self.option_lookup(section, line_lw.lower())
                if option is not None:
                    network_output += ''.join(line).replace(line_lw, option)
            
        return network_output

    def handle_mirrors(self, section='mirrors'):
        """Method handle_mirrors applies specific parsing for mirrors section in preseed template file."""
        mirrors_output = ''
        mirrors_items = dict(self.cfparser.items(section))
        template_lines = self.loaded_template.get(section, False)
        if template_lines:
            for line in template_lines:
                line_lw = line.split()[-1]
                if not line_lw.isupper():
                    mirrors_output += ''.join(line)
                    continue
                option = self.option_lookup(section, line_lw.lower())
                if option is not None:
                    mirrors_output += ''.join(line).replace(line_lw, option)
                    mirrors_items.pop(line_lw.lower(), None)
      
        for mirror in sorted(mirrors_items):
            value = mirrors_items[mirror]
            if mirror.startswith('local') and len(mirror) == 6:
                mirrors_output += 'd-i apt-setup/%s/repository string %s\n' % (mirror, value)
            elif mirror.endswith('_source'):
                mirrors_output += 'd-i apt-setup/%s/source boolean %s\n' % (mirror.split('_')[0], value)
            elif mirror.endswith('_comment'):
                mirrors_output += 'd-i apt-setup/%s/comment string %s\n' % (mirror.split('_')[0], value)
            elif mirror.endswith('_key'):
                mirrors_output += 'd-i apt-setup/%s/key string %s\n' % (mirror.split('_')[0], value)

        return mirrors_output

    def parse_partitions(self, partition_items):
        """Method parse_partitions parses configuration of partitions from INI file."""
        part_names, partitions = [], OrderedDict()
        for partition in sorted(partition_items):
            value = partition_items[partition]
            if len(partition) == 5:
                part_names.append(value)
                partitions[value] = {}
            else:
                part, param = partition.split('_')
                partitions[part_names[int(part[4])]].update({param: value})

        return partitions
        
    def generate_partitions(self, partitions, section='partitioning'):
        # TODO: add option to create separate boot parititon in SW raid (2 sw raid groups)
        """Method generate_partitions generates preseed like specification of partitions
        based on previously parsed input from INI file, which is handled by parse_partitions."""
        partition_output, raid_options = '', []
        if self.option_lookup(section, 'method') == 'raid':
            try:
                for raid_option in ['raid_type', 'raid_spares', 'raid_fs', 'raid_mount', 'use_disks']:
                    raid_options.append(self.cfparser.get(section, raid_option))
            except ConfigParser.NoOptionError as e:
                self.logger.error('Unable to find raid option %s in %s' % (e.option, self.config_file))
                sys.exit(6)

            raid_options[-1] = '#'.join(raid_options[-1].split())
            raid_options.insert(1, len(raid_options[-1].split('#')))
            partition_output += 'd-i partman-auto-raid/recipe string %s %s %s %s %s %s .\n' % tuple(raid_options)
            partition_output += 'd-i partman-auto/expert_recipe string custom :: '
            # numbers 4096, 5000 and -1 are just magic to ensure that raid will reside on all free disk space
            partition_output += '4096 5000 -1 raid $lvmignore{ } method{ raid } . '
        else:
            partition_output += 'd-i partman-auto/expert_recipe string custom :: '

        for partition, attributes in partitions.iteritems():
            partition_config = ''
            try:
                size = attributes['size']
                format = attributes['format']
                partition_config += '%s %s %s %s ' % (size, int(size) + 1, size, format)

                if attributes['lvm'] == 'true':
                    partition_config += '$defaultignore{ } $lvmok{ } '
                else: 
                    partition_config += '$primary{ } $lvmignore{ } '

                if format == 'linux-swap':
                    partition_config += 'method{ swap } format{ } . '
                else:
                    partition_config += 'method{ format } format{ } use_filesystem{ } filesystem{ %s } ' % format

                partition_config += 'mountpoint{ %s } . ' % attributes['mount']
                partition_output += partition_config
            except KeyError as e:
                if e.message == 'mount' and format == 'linux-swap':
                    partition_output += partition_config
                    continue
                else:
                    self.logger.error('Missing %s option in disk configuration, skipping whole partition.' % e)
                    continue

        return partition_output + '\n'

    def handle_partitioning(self, section='partitioning'):
        """Method handle_partitioning applies specific parsing for partitioning section in preseed template file."""
        partitions_output = ''
        partition_items = dict(self.cfparser.items(section))
        template_lines = self.loaded_template.get(section, False)
        if template_lines:
            for line in template_lines:
                line_lw = line.split()[-1]
                if not line_lw.isupper():
                    partitions_output += ''.join(line)
                    continue
                option = self.option_lookup(section, line_lw.lower())
                if option is not None:
                    partitions_output += ''.join(line).replace(line_lw, option)
                    partition_items.pop(line_lw.lower(), None)

        final_partitions = {key: value for key, value in partition_items.iteritems() if key.startswith('part')}
        partitions = self.generate_partitions(self.parse_partitions(final_partitions), section)
        partitions_output += partitions
        return partitions_output 

    def set_logging_level(self, level):
        """Method set_logging_level allows user to define, which log messages to display."""
        try:
            if level == 'QUIET':
                self.logger.disabled = True
            else:
                self.logger.setLevel(getattr(logging, level))
        except AttributeError:
            self.logger.error('No such logging level: %s.' % level)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script parses options from INI file and tries \
        to match them with lines in preseed template file. The main purpose is to simplify disk \
        configuration syntax of partman, which is, by nature, terific at the first glance.')
    parser.add_argument('-q', '--quiet', action='store_true', help='disable console logging to stderr')
    parser.add_argument('-l', '--log-level', action='store', help='set logging level (DEBUG, INFO, WARNING, ERROR). \
        Log messages less severe then specified log level will be ignored')
    parser.add_argument('-c', '--config', action='store', help='read from specified INI file')
    parser.add_argument('-i', '--input', action='store', help='use specified template for preseed generation')
    parser.add_argument('-o', '--output', action='store', help='write preseed to specified file')
    args = parser.parse_args()

    preseed = PreseedCreator(config_file=args.config if args.config else 'config.ini')

    if args.quiet:
        preseed.set_logging_level('QUIET')
    elif args.log_level:
        preseed.set_logging_level(args.log_level)
    
    preseed.read_template(template=args.input if args.input else 'template.cfg')
    output = preseed.create_preseed(output_file=args.output if args.output else None)   
    if output is not None:
        print(output)
