# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida_core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
from abc import ABCMeta
from aiida.common.exceptions import InputValidationError, MultipleObjectsError, NotExistent
from aiida.plugins.factory import BaseFactory
from aiida.common.utils import abstractclassmethod

__all__ = ['CalculationFactory', 'DataFactory', 'WorkflowFactory', 'load_group', 
           'load_node', 'load_workflow', 'BackendDelegateWithDefault']


def CalculationFactory(entry_point):
    """
    Return the Calculation plugin class for a given entry point

    :param entry_point: the entry point name of the Calculation plugin
    """
    return BaseFactory('aiida.calculations', entry_point)


def DataFactory(entry_point):
    """
    Return the Data plugin class for a given entry point

    :param entry_point: the entry point name of the Data plugin
    """
    return BaseFactory('aiida.data', entry_point)


def WorkflowFactory(entry_point):
    """
    Return the Workflow plugin class for a given entry point

    :param entry_point: the entry point name of the Workflow plugin
    """
    return BaseFactory('aiida.workflows', entry_point)


def create_node_id_qb(node_id=None, pk=None, uuid=None, parent_class=None, query_with_dashes=True):
    """
    Returns the QueryBuilder instance set to retrieve AiiDA objects given their
    (parent)class and PK (in which case the object should be unique) or UUID
    or UUID starting pattern.

    :param node_id: PK (integer) or UUID (string) or a node
    :param pk: PK of a node
    :param uuid: UUID of a node, or the beginning of the uuid
    :param parent_class: if specified, looks only among objects that are instances of
    	a subclass of parent_class, otherwise among nodes
    :param bool query_with_dashes: Specific if uuid is passed, allows to
        put the uuid in the correct form. Default=True

    :return: a QueryBuilder instance
    """
    # This must be done inside here, because at import time the profile
    # must have been already loaded. If you put it at the module level,
    # the implementation is frozen to the default one at import time.
    from aiida.orm.implementation import Node
    from aiida.orm.querybuilder import QueryBuilder

    # First checking if the inputs are valid:
    inputs_provided = [val is not None for val in (node_id, pk, uuid)].count(True)
    if inputs_provided == 0:
        raise InputValidationError("one of the parameters 'node_id', 'pk' and 'uuid' has to be supplied")
    elif inputs_provided > 1:
        raise InputValidationError("only one of parameters 'node_id', 'pk' and 'uuid' has to be supplied")

    # In principle, I can use this function to fetch any kind of AiiDA object,
    # but if I don't specify anything, I assume that I am looking for nodes
    class_ = parent_class or Node

    # The logic is as follows: If pk is specified I will look for the pk
    # if UUID is specified for the uuid.
    # node_id can either be string -> uuid or an integer -> pk
    # Checking first if node_id specified
    if node_id is not None:
        if isinstance(node_id, (str, unicode)):
            uuid = node_id
        elif isinstance(node_id, int):
            pk = node_id
        else:
            raise TypeError("'node_id' has to be either string, unicode or "
                                 "integer, {} given".format(type(node_id)))

    # Check whether uuid, if supplied, is a string
    if uuid is not None:
        if not isinstance(uuid,(str, unicode)):
            raise TypeError("'uuid' has to be string or unicode")
    # Or whether the pk, if provided, is an integer
    elif pk is not None:
        if not isinstance(pk, int):
            raise TypeError("'pk' has to be an integer")
    else:
        # I really shouldn't get here
        assert True,  "Neither pk  nor uuid was provided"

    qb = QueryBuilder()
    qb.append(class_, tag='node')

    if pk:
        qb.add_filter('node',  {'id': pk})
    elif uuid:
        # Put back dashes in the right place
        start_uuid = uuid.replace('-', '')
        # TODO (only if it brings any speed advantage) add a check on the number of characters
        # to recognize if the uuid pattern is complete. If so, the filter operator can be '=='
        if query_with_dashes:
            # Essential that this is ordered from largest to smallest!
            for dash_pos in [20, 16, 12, 8]:
                if len(start_uuid) > dash_pos:
                    start_uuid = '{}-{}'.format(
                        start_uuid[:dash_pos], start_uuid[dash_pos:]
                        )

        qb.add_filter('node', {'uuid': {'like': '{}%'.format(start_uuid)}})

    return qb


def load_group(group_id=None, pk=None, uuid=None, query_with_dashes=True):
    """
    Load a group by its pk or uuid

    :param group_id: pk (integer) or uuid (string) of a group
    :param pk: pk of a group
    :param uuid: uuid of a group, or the beginning of the uuid
    :param bool query_with_dashes: allow to query for a uuid with dashes (default=True)
    :returns: the requested group if existing and unique
    :raise InputValidationError: if none or more than one of the arguments are supplied
    :raise TypeError: if the wrong types are provided
    :raise NotExistent: if no matching Node is found.
    :raise MultipleObjectsError: if more than one Node was found
    """
    from aiida.orm import Group

    kwargs = {
        'node_id': group_id,
        'pk': pk,
        'uuid': uuid,
        'parent_class': Group,
        'query_with_dashes': query_with_dashes
    }

    qb = create_node_id_qb(**kwargs)
    qb.add_projection('node', '*')
    qb.limit(2)

    try:
        return qb.one()[0]
    except MultipleObjectsError:
        raise MultipleObjectsError('More than one group found. Provide longer starting pattern for uuid.')
    except NotExistent:
        raise NotExistent('No group was found')


def load_node(node_id=None, pk=None, uuid=None, parent_class=None, query_with_dashes=True):
    """
    Load a node by its pk or uuid

    :param node_id: PK (integer) or UUID (string) or a node
    :param pk: PK of a node
    :param uuid: UUID of a node, or the beginning of the uuid
    :param parent_class: if specified, checks whether the node loaded is a
        subclass of parent_class
    :param bool query_with_dashes: allow to query for a uuid with dashes (default=True)
    :returns: the requested node if existing, unique, and (sub)instance of parent_class
    :raise InputValidationError: if none or more than one of the arguments are supplied
    :raise TypeError: if the wrong types are provided
    :raise NotExistent: if no matching Node is found.
    :raise MultipleObjectsError: if more than one Node was found

    """
    from aiida.orm.implementation import Node

    # I can use this functions to load only nodes, i.e. not users, groups etc ...
    # If nothing is specified I assume the big granpa: Node!
    class_ = parent_class or Node
    if not issubclass(class_,  Node):
        raise TypeError("{} is not a subclass of {}".format(class_, Node))

    kwargs = {
        'node_id': node_id,
        'pk': pk,
        'uuid': uuid,
        'parent_class': parent_class,
        'query_with_dashes': query_with_dashes
    }

    qb = create_node_id_qb(**kwargs)
    qb.add_projection('node', '*')
    qb.limit(2)

    try:
        return qb.one()[0]
    except MultipleObjectsError:
        raise MultipleObjectsError('More than one node found. Provide longer starting pattern for uuid.')
    except NotExistent:
        raise NotExistent('No node was found')


def load_workflow(wf_id=None, pk=None, uuid=None):
    """
    Return an AiiDA workflow given PK or UUID.

    :param wf_id: PK (integer) or UUID (string) or UUID instance or a workflow
    :param pk: PK of a workflow
    :param uuid: UUID of a workflow
    :return: an AiiDA workflow
    :raises: ValueError if none or more than one of parameters is supplied
        or type of wf_id is neither string nor integer
    """
    # This must be done inside here, because at import time the profile
    # must have been already loaded. If you put it at the module level,
    # the implementation is frozen to the default one at import time.
    from aiida.orm.implementation import Workflow
    from uuid import UUID as uuid_type

    if int(wf_id is None) + int(pk is None) + int(uuid is None) == 3:
        raise ValueError("one of the parameters 'wf_id', 'pk' and 'uuid' "
                         "has to be supplied")
    if int(wf_id is None) + int(pk is None) + int(uuid is None) < 2:
        raise ValueError("only one of parameters 'wf_id', 'pk' and 'uuid' "
                         "has to be supplied")

    if wf_id is not None:
        if wf_id and isinstance(wf_id, uuid_type):
            wf_id = str(wf_id)

        if isinstance(wf_id, basestring):
            return Workflow.get_subclass_from_uuid(wf_id)
        elif isinstance(wf_id, int):
            return Workflow.get_subclass_from_pk(wf_id)
        else:
            raise ValueError("'wf_id' has to be either string, unicode, "
                             "integer or UUID instance, {} given".format(type(wf_id)))
    if pk is not None:
        if isinstance(pk, int):
            return Workflow.get_subclass_from_pk(pk)
        else:
            raise ValueError("'pk' has to be an integer")
    else:
        if uuid and isinstance(uuid, uuid_type):
            uuid = str(uuid)
        if isinstance(uuid, str) or isinstance(uuid, unicode):
            return Workflow.get_subclass_from_uuid(uuid)
        else:
            raise ValueError("'uuid' has to be a string, unicode or a UUID instance")


class BackendDelegateWithDefault(object):
    """
    This class is a helper to implement the delegation pattern [1] by
    delegating functionality (i.e. calling through) to the backend class
    which will do the actual work.

    [1] https://en.wikipedia.org/wiki/Delegation_pattern
    """
    __metaclass__ = ABCMeta

    _DEFAULT = None

    @abstractclassmethod
    def create_default(cls):
        raise NotImplementedError("The subclass should implement this")

    @classmethod
    def get_default(cls):
        if cls._DEFAULT is None:
            cls._DEFAULT = cls.create_default()
        return cls._DEFAULT

    def __init__(self, backend):
        self._backend = backend
