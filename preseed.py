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

    def handle_partitioning(self, section='partitioning'):
        """Method handle_partitioning applies specific parsing for partitioning section in preseed template file."""
        partitions_output = ''
        template_lines = self.loaded_template.get(section, False)
        if not template_lines:
            self.logger.warning('No %s section found in template file, skipping.' % (section))
            return '\n'
        
        for line in template_lines:
            line_lw = line.split()[-1]
            if not line_lw.isupper():
                partitions_output += ''.join(line)
                continue
            option = self.option_lookup(section, line_lw.lower())
            if option is not None:
                partitions_output += ''.join(line).replace(line_lw, option)

        partman = PartmanCreator(section, self.cfparser, self.logger)
        if self.option_lookup(section, 'method') == 'raid':
            partitions_output += partman.preload_raid_groups()
        else:
            partitions_output += 'd-i partman-auto/expert_recipe string custom :: '
        partitions_output += partman.preload_partitions()
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


class PartmanCreator(object):
    """PartmanCreator class handles most complicated part of a preseeding, which is partman itself.
    PartmanCreator uses simple options from INI configuration file. These options define raid groups
    and partitions with prefix (raidgX, partX) followed by an option. For example raidg0_type."""

    def __init__(self, section, cfparser, logger):
        self.section = section
        self.cfparser = cfparser
        self.logger = logger
        self.partition_options = self.cfparser.options(self.section)
        self.has_lvm = False

    def load_option(self, option):
        """Method load_options is simple wrapper for ConfigParser's get method. If value is not found
        within INI file, False is provided in return for later checking and settings defaults."""
        try:
            return self.cfparser.get(self.section, option)
        except ConfigParser.NoOptionError:
            return False

    def preload_raid_groups(self):
        """Method preload_raid_groups loads and parses configuration of raid groups. First raid group is always
        created as a primary. Last defined raid group will get all unallocated space."""
        index, raid_output = 0, 'd-i partman-auto-raid/recipe string '
        raid_groups = 0
        while index is not None:
            r_type = self.load_option('raidg%d_type' % index)
            r_disks = self.load_option('raidg%d_disks' % index) 
            r_spares = self.load_option('raidg%d_spares' % index) or 0
            r_fs = self.load_option('raidg%d_fs' % index) or 'ext4'
            if r_fs == 'lvm':
                self.has_lvm = True
            r_mount = self.load_option('raidg%d_mount' % index) or '-'
            if r_type:
                raid_output += '%s %s %s %s %s ' % (r_type, len(r_disks.split()), r_spares, r_fs, r_mount)
                raid_output += '%s . ' % ('#'.join(r_disks.split()))
                index += 1
            else:
                self.logger.info('Partman created %d raid groups.' % (index))
                raid_groups = index
                index = None
        
        if raid_groups:
            raid_output += '\nd-i partman-auto/expert_recipe string custom :: '
            for rg in range(1, raid_groups + 1):
                size = int(self.load_option('raidg%d_size' % (rg - 1)))
                if not size:
                    self.logger.error('Unable to find raidg%d size definition, exiting.' % (rg - 1))
                    sys.exit(5)

                raid_output += '%d %d %d raid ' % (size, size + 1, size if rg != raid_groups else -1)
                raid_output += '$primary{ } ' if rg == 1 else ''
                raid_output += '$lvmignore{ } method{ raid } . '
        else:
            self.logger.error('Unable to find raid definitions, exiting.')
            sys.exit(5)

        return raid_output
                
    def preload_partitions(self):
        """Method preload_partitions loads and parses configuration of parititons. Last defined partition will get all
        unallocated space."""
        index, part_output = 0, ''
        while index is not None:
            p = self.load_option('part%d' % index)
            p_fs = self.load_option('part%d_fs' % index) or 'ext4'
            p_mount = self.load_option('part%d_mount' % index) or None
            p_size = int(self.load_option('part%d_size' % index)) or 1024
            p_lvm = self.load_option('part%d_lvm' % index) or 'false'
            if p:
                part_output += '%d %d ' % (p_size, p_size + 1)
                part_output += '%d %s ' % (p_size, p_fs)
                part_output += '$defaultignore{ } $lvmok{ } ' if p_lvm == 'true' else '$primary{ } $lvmignore{ } '
                if p_fs == 'linux-swap':
                    part_output += 'method{ swap } format{ } '
                else:
                    part_output += 'method{ format } format{ } use_filesystem{ } filesystem{ %s } ' % p_fs

                part_output += 'mountpoint{ %s } . ' % p_mount if p_mount is not None else '. '
                index += 1
            else:
                self.logger.info('Partman created %d partitions.' % (index))
                index = None
       
        if self.has_lvm:
            part_output += '1 2048 -1 ext4 method{ format } $defaultignore{ } $lvmok{ } lv_name{ todelete } . ' 
        return part_output + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script parses options from INI file and tries \
        to match them with lines in preseed template file. The main purpose is to simplify disk \
        configuration syntax of partman, which is, by nature, terific at the first glance.')
    parser.add_argument('-q', '--quiet', action='store_true', help='disable console logging to stderr')
    parser.add_argument('-l', '--log-level', action='store', help='set logging level (DEBUG, INFO, WARNING, ERROR). \
        Log messages less severe then specified log level will be ignored')
    parser.add_argument('-i', '--input', action='store', help='read from specified INI file')
    parser.add_argument('-t', '--template', action='store', help='use specified template for preseed generation')
    parser.add_argument('-o', '--output', action='store', help='write preseed to specified file')
    args = parser.parse_args()

    preseed = PreseedCreator(config_file=args.input if args.input else 'config.ini')

    if args.quiet:
        preseed.set_logging_level('QUIET')
    elif args.log_level:
        preseed.set_logging_level(args.log_level)
    
    preseed.read_template(template=args.template if args.template else 'template.cfg')
    output = preseed.create_preseed(output_file=args.output if args.output else None)   
    if output is not None:
        print(output)
