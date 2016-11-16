"""
"""

# Created on 2013.07.24
#
# Author: Giovanni Cannata
#
# Copyright 2013, 2014, 2015, 2016 Giovanni Cannata
#
# This file is part of ldap3.
#
# ldap3 is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ldap3 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with ldap3 in the COPYING and COPYING.LESSER files.
# If not, see <http://www.gnu.org/licenses/>.

from .. import SEQUENCE_TYPES, CLASSES_EXCLUDED_FROM_CHECK, ATTRIBUTES_EXCLUDED_FROM_CHECK, STRING_TYPES
from ..core.exceptions import LDAPControlError, LDAPAttributeError, LDAPObjectClassError
from ..protocol.rfc4511 import Controls, Control
from ..utils.conv import to_raw, escape_filter_chars

def attribute_to_dict(attribute):
    return {'type': str(attribute['type']), 'values': [str(val) for val in attribute['vals']]}


def attributes_to_dict(attributes):
    attributes_dict = dict()
    for attribute in attributes:
        attribute_dict = attribute_to_dict(attribute)
        attributes_dict[attribute_dict['type']] = attribute_dict['values']
    return attributes_dict


def referrals_to_list(referrals):
    return [str(referral) for referral in referrals if referral] if referrals else None


def search_refs_to_list(search_refs):
    return [str(search_ref) for search_ref in search_refs if search_ref] if search_refs else None


def sasl_to_dict(sasl):
    return {'mechanism': str(sasl['mechanism']), 'credentials': str(sasl['credentials'])}


def authentication_choice_to_dict(authentication_choice):
    return {'simple': str(authentication_choice['simple']) if authentication_choice.getName() == 'simple' else None, 'sasl': sasl_to_dict(authentication_choice['sasl']) if authentication_choice.getName() == 'sasl' else None}


def decode_referrals(referrals):
    return [str(referral) for referral in referrals if referral] if referrals else None


def partial_attribute_to_dict(modification):
    return {'type': str(modification['type']), 'value': [str(value) for value in modification['vals']]}


def change_to_dict(change):
    return {'operation': int(change['operation']), 'attribute': partial_attribute_to_dict(change['modification'])}


def changes_to_list(changes):
    return [change_to_dict(change) for change in changes]


def attributes_to_list(attributes):
    return [str(attribute) for attribute in attributes]


def ava_to_dict(ava):
    return {'attribute': str(ava['attributeDesc']), 'value': str(ava['assertionValue'])}


def substring_to_dict(substring):
    return {'initial': substring['initial'] if substring['initial'] else '', 'any': [middle for middle in substring['any']] if substring['any'] else '', 'final': substring['final'] if substring['final'] else ''}


def prepare_changes_for_request(changes):
    prepared = dict()
    for change in changes:
        prepared[change['attribute']['type']] = (change['operation'], change['attribute']['value'])
    return prepared


def build_controls_list(controls):
    """
    controls is a list of Control() or tuples
    each tuple must have 3 elements: the control OID, the criticality, the value
    criticality must be a boolean
    """
    if not controls:
        return None

    if not isinstance(controls, SEQUENCE_TYPES):
        raise LDAPControlError('controls must be a sequence')

    built_controls = Controls()
    for idx, control in enumerate(controls):
        if isinstance(control, Control):
            built_controls.setComponentByPosition(idx, control)
        elif len(control) == 3 and isinstance(control[1], bool):
            built_control = Control()
            built_control['controlType'] = control[0]
            built_control['criticality'] = control[1]
            if control[2] is not None:
                built_control['controlValue'] = control[2]
            built_controls.setComponentByPosition(idx, built_control)
        else:
            raise LDAPControlError('control must be a tuple of 3 elements: controlType, criticality (boolean) and controlValue (None if not provided)')

    return built_controls


def validate_assertion_value(schema, name, value, auto_escape):
    value = validate_attribute_value(schema, name, value, auto_escape)

    if b'\\' in value:
        validated_value = bytearray()
        pos = 0
        while pos < len(value):
            if value[pos] == 92 or value[pos] == b'\\':  # asc for \ in python 3
                byte = value[pos + 1: pos + 3]
                if len(byte) == 2:
                    try:
                        validated_value.append(int(value[pos + 1: pos + 3], 16))
                        pos += 3
                        continue
                    except ValueError:
                        pass
            if isinstance(value, STRING_TYPES):
                validated_value += value[pos].encode('utf-8')
            else:
                validated_value += chr(value[pos]).encode('utf-8')
            pos += 1
        validated_value = bytes(validated_value)
    else:
        validated_value = value

    return validated_value


def validate_attribute_value(schema, name, value, auto_escape):
    if schema:
        if schema.attribute_types is not None and name not in schema.attribute_types and name not in ATTRIBUTES_EXCLUDED_FROM_CHECK:
            raise LDAPAttributeError('invalid attribute ' + name)
        if schema.object_classes is not None and name == 'objectClass':
            if value not in CLASSES_EXCLUDED_FROM_CHECK and value not in schema.object_classes:
                raise LDAPObjectClassError('invalid class in objectClass attribute: ' + value)
    if auto_escape:
        value = escape_filter_chars(value)  # tries to convert from local encoding
    return to_raw(value)
