__copyright__ = 'Copyright (C) 2019, Nokia'


class MetaSingleton(type):
    def __call__(cls, *args, **kwargs):
        if 'instance' not in cls.__dict__:
            cls.instance = super(MetaSingleton, cls).__call__(*args, **kwargs)
        return cls.instance
