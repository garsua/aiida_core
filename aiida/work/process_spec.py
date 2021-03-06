# -*- coding: utf-8 -*-
from collections import defaultdict

import plumpy

from aiida.common.extendeddicts import FixedFieldsAttributeDict
from aiida.orm.data.parameter import ParameterData
from aiida.work.ports import InputPort, PortNamespace


class ProcessSpec(plumpy.ProcessSpec):
    """
    Contains the inputs, outputs and outline of a process.
    """

    INPUT_PORT_TYPE = InputPort
    PORT_NAMESPACE_TYPE = PortNamespace

    def __init__(self):
        super(ProcessSpec, self).__init__()
        self._exposed_inputs = defaultdict(lambda: defaultdict(list))
        self._exposed_outputs = defaultdict(lambda: defaultdict(list))

    def expose_inputs(self, process_class, namespace=None, exclude=(), include=None):
        """
        This method allows one to automatically add the inputs from another
        Process to this ProcessSpec. The optional namespace argument can be
        used to group the exposed inputs in a separated PortNamespace

        :param process_class: the Process class whose inputs to expose
        :param namespace: a namespace in which to place the exposed inputs
        :param exclude: list or tuple of input keys to exclude from being exposed
        """
        self._expose_ports(
            process_class=process_class,
            source=process_class.spec().inputs,
            destination=self.inputs,
            expose_memory=self._exposed_inputs,
            namespace=namespace,
            exclude=exclude,
            include=include
        )

    def expose_outputs(self, process_class, namespace=None, exclude=(), include=None):
        """
        This method allows one to automatically add the ouputs from another
        Process to this ProcessSpec. The optional namespace argument can be
        used to group the exposed outputs in a separated PortNamespace.

        :param process_class: the Process class whose inputs to expose
        :param namespace: a namespace in which to place the exposed inputs
        :param exclude: list or tuple of input keys to exclude from being exposed
        """
        self._expose_ports(
            process_class=process_class,
            source=process_class.spec().outputs,
            destination=self.outputs,
            expose_memory=self._exposed_outputs,
            namespace=namespace,
            exclude=exclude,
            include=include
        )

    def _expose_ports(
        self,
        process_class,
        source,
        destination,
        expose_memory,
        namespace,
        exclude,
        include
    ):
        if namespace:
            port_namespace = destination.create_port_namespace(namespace)
        else:
            port_namespace = destination
        exposed_list = expose_memory[namespace][process_class]

        for name, port in self._filter_names(
            source.iteritems(),
            exclude=exclude,
            include=include
        ):
            port_namespace[name] = port
            exposed_list.append(name)

    @staticmethod
    def _filter_names(items, exclude, include):
        if exclude and include is not None:
            raise ValueError('exclude and include are mutually exclusive')

        for name, port in items:
            if include is not None:
                if name not in include:
                    continue
            else:
                if name in exclude:
                    continue
            yield name, port
