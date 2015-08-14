import sys
from collections import OrderedDict
import ConfigParser
import logging


class PreseedCreator(object):
    """PreseedCreator class handles loading of template and configuration files. Based on the 
    mentioned files, PreseedCreator then builds Debian's preseed for ISO images. Preseed 
    files are used during phase of Debian installation to preload installer with 
    already answered questions about system setup."""

    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        logging.basicConfig(format='%(asctime)-15s %(levelname)s: %(message)s')
        self.logger = logging.getLogger('preseed_output')
        self.logger.setLevel(logging.INFO)
        self.cfparser = ConfigParser.ConfigParser()
        try:
            self.cfparser.read(self.config_file)
        except ConfigParser.ParsingError:
            self.logger.error('Unable to parse file {}'.format(self.config_file))
            sys.exit(1)
        self.loaded_template = OrderedDict()
        # special functions are handled by handle_X methods 
        self.special_sections = ['network', 'mirrors', 'partitioning']

    def read_template(self, template='template.cfg'):
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
            self.logger.error('No such file {}'.format(template))
            sys.exit(1)

    def option_lookup(self, section, option):
        """Method option_lookup wraps ConfigParser.get method and adds error handling and logging."""
        try:
            return self.cfparser.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            self.logger.info('{} option was not found predefined in {}, skipping.'.format(option, self.config_file))
            return None 

    def create_preseed(self, output_file='preseed.cfg'):
        """Method create_preseed builds preseed configuration based on previously loaded template 
        file and options defined in INI configuration file."""
        if not self.loaded_template:
            self.logger.error('No template was preloaded.')
            sys.exit(2)

        preseed_output = ''
        for section in self.cfparser.sections():
            if section in self.special_sections:
                handle_function = getattr(self, 'handle_{}'.format(section), False)
                if handle_function:
                    preseed_output += handle_function(section)
                else:
                    self.logger.warning('No handler found for section {}, skipping.'.format(section))
            else:
                template_lines = self.loaded_template.get(section, False)
                if template_lines:
                    for line in template_lines:
                        line = line.split()
                        if not line[-1].isupper():
                            continue
                        option = self.option_lookup(section, line[-1].lower())
                        if option is not None:
                            preseed_output += ' '.join(line).replace(line[-1], option) + '\n'

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
                    continue
                option = self.option_lookup(section, line_lw.lower())
                if option is not None:
                    mirrors_output += ''.join(line).replace(line_lw, option)
                    mirrors_items.pop(line_lw.lower(), None)
      
        for mirror in sorted(mirrors_items):
            value = mirrors_items[mirror]
            if mirror.startswith('local') and len(mirror) == 6:
                mirrors_output += 'd-i apt-setup/{}/repository string {}\n'.format(mirror, value)
            elif mirror.endswith('_source'):
                mirrors_output += 'd-i apt-setup/{}/source boolean {}\n'.format(mirror.split('_')[0], value)

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
        """Method generate_partitions generates preseed like specification of partitions
        based on previously parsed input from INI file, which is handled by parse_partitions."""
        partition_output = 'd-i partman-auto/expert_recipe string custom :: '
        method = self.option_lookup(section, 'method')
        if method == 'raid':
            partition_output += '4096 5000 -1 raid $lvmignore{ } method{ raid } . '
        for partition, attributes in partitions.iteritems():
            partition_config = ''
            try:
                min, max = attributes['size'].split(',')    
                partition_config += '%s %s %s ' % (min, int(min) + 1, str(max).lstrip())

                format = attributes['format']
                partition_config += '%s ' % format

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
                    self.logger.error('Missing {} option in disk configuration, skipping whole partition.'.format(e))
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
                    continue
                option = self.option_lookup(section, line_lw.lower())
                if option is not None:
                    partitions_output += ''.join(line).replace(line_lw, option)
                    partition_items.pop(line_lw.lower(), None)

        partitions = self.generate_partitions(self.parse_partitions(partition_items), section)
        partitions_output += partitions
        return partitions_output 

    def set_logging_level(self, level):
        try:
            self.logger.setLevel(getattr(logging, level))
        except AttributeError:
            self.logger.error('No such logging level: {}.'.format(level))

    def test(self):
        print(self.cfparser.options('localization'))
        print(OrderedDict(self.cfparser.items('mirrors')))
        print(self.cfparser.sections())
    

if __name__ == '__main__':
    x = PreseedCreator()
    x.read_template()
    print x.create_preseed()   

#TODO:
#   - argparse
#   - change string .format to older % formatter
