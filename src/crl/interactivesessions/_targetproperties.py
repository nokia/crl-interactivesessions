__copyright__ = 'Copyright (C) 2019, Nokia'


class _TargetProperties(object):

    defaultproperties = {'termination_timeout': 10,
                         'prompt_timeout': 30,
                         'default_executable': '/bin/bash',
                         'max_processes_in_target': 100,
                         'update_env_dict': {}}

    def __init__(self):
        self._props = self.defaultproperties.copy()

    def __getattr__(self, name):
        return self.get_property(name)

    def set_property(self, name, value):
        if name not in self.defaultproperties:
            raise AttributeError(
                "Property '{}' not in defaultproperties".format(name))
        self._props[name] = value

    def get_property(self, name):
        try:
            return self._props[name]
        except KeyError:
            raise AttributeError("Property '{}' not found".format(name))

    @property
    def properties(self):
        return self._props.copy()

    @classmethod
    def set_default_property(cls, property_name, property_value):
        cls.defaultproperties[property_name] = property_value
