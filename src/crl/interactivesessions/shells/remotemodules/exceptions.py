__copyright__ = 'Copyright (C) 2019, Nokia'


class ExitFromServe(Exception):
    pass


class FatalPythonError(Exception):
    def __str__(self):
        return '{cls}: {msg}'.format(
            cls=self.__class__.__name__,
            msg=super(FatalPythonError, self).__str__())
