# -*- coding: utf-8 -*-
from collections import Mapping
from aiida.work.ports import PortNamespace

__all__ = ['ProcessBuilder', 'JobProcessBuilder', 'ProcessBuilderNamespace']


class ProcessBuilderNamespace(Mapping):
    """
    Input namespace for the ProcessBuilder. Dynamically generates the getters and setters
    for the input ports of a given PortNamespace
    """

    def __init__(self, port_namespace):
        self._valid_fields = port_namespace.keys()
        self._port_namespace = port_namespace
        self._data = {}

        for name, port in port_namespace.items():

            if isinstance(port, PortNamespace):
                self._data[name] = ProcessBuilderNamespace(port)
                def fgetter(self, name=name):
                    return self._data.get(name)
            elif port.has_default():
                def fgetter(self, name=name, default=port.default):
                    return self._data.get(name, default)
            else:
                def fgetter(self, name=name):
                    return self._data.get(name, None)

            def fsetter(self, value):
                self._data[name] = value

            fgetter.__doc__ = str(port)
            getter = property(fgetter)
            getter.setter(fsetter)
            setattr(self.__class__, name, getter)

    def __setattr__(self, attr, value):
        """
        Any attributes without a leading underscore being set correspond to inputs and should hence
        be validated with respect to the corresponding input port from the process spec
        """
        if attr.startswith('_'):
            object.__setattr__(self, attr, value)
        else:
            port = self._port_namespace[attr]
            is_valid, message = port.validate(value)

            if not is_valid:
                raise ValueError('invalid attribute value: {}'.format(message))

            self._data[attr] = value

    def __repr__(self):
        return self._data.__repr__()

    def __dir__(self):
        return sorted(set(self._valid_fields + [n for n in self.__dict__.keys() if n.startswith('_')]))

    def __iter__(self):
       for k, v in self._data.items():
          yield k

    def __len__(self):
        return len(self._data)

    def __getitem__(self, item):
        return self._data[item]


class ProcessBuilder(ProcessBuilderNamespace):
    """
    A process builder that helps creating a new calculation
    """
    def __init__(self, process_class):
        self._process_class = process_class
        self._process_spec = self._process_class.spec()
        super(ProcessBuilder, self).__init__(port_namespace=self._process_spec.inputs)


class JobProcessBuilder(ProcessBuilder):
    """
    A process builder specific to JobCalculation classes, that provides
    also the submit_test functionality
    """
    def __dir__(self):
        return super(JobProcessBuilder, self).__dir__() + ['submit_test']

    def submit_test(self, folder=None, subfolder_name=None):
        """
        Run a test submission by creating the files that would be generated for the real calculation in a local folder,
        without actually storing the calculation nor the input nodes. This functionality therefore also does not
        require any of the inputs nodes to be stored yet.

        :param folder: a Folder object, within which to create the calculation files. By default a folder
            will be created in the current working directory
        :param subfolder_name: the name of the subfolder to use within the directory of the ``folder`` object. By
            default a unique string will be generated based on the current datetime with the format ``yymmdd-``
            followed by an auto incrementing index
        """
        inputs = {
            'store_provenance': False
        }
        inputs.update(**self)
        process = self._process_class(inputs=inputs)

        return process._calc.submit_test(folder, subfolder_name)
