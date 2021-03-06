#!/usr/bin/env python3
"""Classe to manage SNMP agent configurations."""

# Standard imports
from copy import deepcopy

# Import project libraries
from pattoo_shared import configuration, files, log
from pattoo_shared.configuration import Config
from pattoo_shared.variables import IPTargetPollingPoints
from pattoo_agent_snmp import PATTOO_AGENT_SNMPD, PATTOO_AGENT_SNMP_IFMIBD
from pattoo_agent_snmp.variables import SNMPAuth, SNMPVariableList


class ConfigSNMP(Config):
    """Class gathers all configuration information."""

    def __init__(self):
        """Initialize the class.

        Args:
            None

        Returns:
            None

        """
        # Instantiate inheritance
        Config.__init__(self)

        # Get the configuration directory
        config_file = configuration.agent_config_filename(
            PATTOO_AGENT_SNMPD)
        self._agent_config = files.read_yaml_file(config_file)

    def snmpvariables(self):
        """Get list of dicts of SNMP information in configuration file.

        Args:
            group: Group name to filter results by

        Returns:
            result: List of SNMPVariable items

        """
        # Get result
        result = _snmpvariables(self._agent_config)
        return result

    def target_polling_points(self):
        """Get list of dicts of SNMP information in configuration file.

        Args:
            group: Group name to filter results by

        Returns:
            result: List of IPTargetPollingPoints objects

        """
        # Get result
        result = _target_polling_points(self._agent_config)
        return result

    def polling_interval(self):
        """Get targets.

        Args:
            None

        Returns:
            result: result

        """
        # Get parameter
        key = 'polling_interval'
        result = self._agent_config.get(key, 300)
        result = abs(int(result))
        return result


class ConfigSNMPIfMIB(Config):
    """Class gathers all configuration information."""

    def __init__(self):
        """Initialize the class.

        Args:
            None

        Returns:
            None

        """
        # Instantiate inheritance
        Config.__init__(self)

        # Get the configuration directory
        config_file = configuration.agent_config_filename(
            PATTOO_AGENT_SNMP_IFMIBD)
        self._agent_config = files.read_yaml_file(config_file)

    def snmpvariables(self):
        """Get list of dicts of SNMP information in configuration file.

        Args:
            group: Group name to filter results by

        Returns:
            result: List of SNMPVariable items

        """
        # Get result
        result = _snmpvariables(self._agent_config)
        return result

    def target_polling_points(self):
        """Get list of dicts of SNMP information in configuration file.

        Args:
            group: Group name to filter results by

        Returns:
            result: List of IPTargetPollingPoints objects

        """
        # Get result
        result = _target_polling_points(self._agent_config)
        return result

    def polling_interval(self):
        """Get targets.

        Args:
            None

        Returns:
            result: result

        """
        # Get parameter
        key = 'polling_interval'
        result = self._agent_config.get(key, 300)
        result = abs(int(result))
        return result


def _target_polling_points(_configuration):
    """Get list of dicts of SNMP information in configuration file.

    Args:
        _configuration: Configuration to process

    Returns:
        result: List of IPTargetPollingPoints objects

    """
    # Initialize key variables
    result = []
    datapoint_key = 'oids'

    # Get configuration snippet
    key = 'polling_groups'
    sub_config = _configuration.get(key)

    if sub_config is None:
        log_message = '''\
"{}" parameter not found in configuration file. Will not poll.'''
        log.log2info(55000, log_message)
        return result

    # Create snmp objects
    groups = _validate_oids(sub_config)
    for group in groups:
        # Ignore bad values
        if isinstance(group, dict) is False:
            continue

        # Process data
        if 'ip_targets' and datapoint_key in group:
            for ip_target in group['ip_targets']:
                poll_targets = configuration.get_polling_points(
                    group[datapoint_key])
                dpt = IPTargetPollingPoints(ip_target)
                dpt.add(poll_targets)
                if dpt.valid is True:
                    result.append(dpt)
    return result


def _snmpvariables(_configuration):
    """Get list of dicts of SNMP information in configuration file.

    Args:
        _configuration: Configuration to process

    Returns:
        result: List of SNMPVariable items

    """
    # Initialize key variables
    result = []

    # Get configuration snippet
    key = 'auth_groups'
    sub_config = _configuration.get(key)

    if sub_config is None:
        log_message = '''\
"{}" parameter not found in configuration file. Will not poll.'''
        log.log2info(55001, log_message)
        return result

    # Create snmp objects
    groups = _validate_snmp(sub_config)
    for group in groups:
        # Save the authentication parameters
        snmpauth = SNMPAuth(
            version=group.get('snmp_version', 2),
            community=group.get('snmp_community', 'public'),
            port=group.get('snmp_port', 161),
            secname=group.get('snmp_secname'),
            authprotocol=group.get('snmp_authprotocol'),
            authpassword=group.get('snmp_authpassword'),
            privprotocol=group.get('snmp_privprotocol'),
            privpassword=group.get('snmp_privpassword')
        )

        # Create the SNMPVariableList
        snmpvariablelist = SNMPVariableList(snmpauth, group['ip_targets'])
        snmpvariables = snmpvariablelist.snmpvariables
        result.extend(snmpvariables)

    # Return
    return result


def _validate_snmp(config_dict):
    """Get list of dicts of SNMP information in configuration file.

    Args:
        config_dict: Configuration dict

    Returns:
        data: List of SNMP data dicts found in configuration file.

    """
    # Initialize key variables
    seed_dict = {}
    seed_dict['ip_targets'] = []

    # Start populating information
    data = []
    for read_dict in config_dict:
        # Next entry if this is not a dict
        if isinstance(read_dict, dict) is False:
            continue

        # Assign data
        new_dict = deepcopy(seed_dict)
        for key in read_dict.keys():
            new_dict[key] = read_dict[key]

        # Verify the correct version keys
        if new_dict['snmp_version'] not in [2, 3]:
            continue

        # Validate IP addresses and OIDs
        if isinstance(new_dict['ip_targets'], list) is False:
            continue

        # Append data to list
        data.append(new_dict)

    # Return
    return data


def _validate_oids(config_dict):
    """Get list of dicts of SNMP information in configuration file.

    Args:
        config_dict: Configuration dict

    Returns:
        snmp_data: List of SNMP data dicts found in configuration file.

    """
    # Initialize key variables
    seed_dict = {}
    seed_dict['ip_targets'] = []
    seed_dict['oids'] = []

    # Start populating information
    data = []

    # Ignore incompatible configuration
    if isinstance(config_dict, list) is False:
        return []

    # Process the stuff
    for read_dict in config_dict:
        # Next entry if this is not a dict
        if isinstance(read_dict, dict) is False:
            continue

        # Assign data
        new_dict = deepcopy(seed_dict)
        for key, value in sorted(read_dict.items()):
            if key not in seed_dict.keys():
                continue
            if isinstance(read_dict[key], list) is True:
                new_dict[key] = value

        # Append data to list
        data.append(new_dict)

    # Return
    return data
