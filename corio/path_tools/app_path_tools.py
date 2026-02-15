import appdirs

from fmtr.tools.path_tools import Path


class AppPaths:
    """

    Wrap appdirs to return Path objects

    """
    PathType = Path

    def user_data_dir(self, appname=None, appauthor=None, version=None, roaming=False):
        path_str = appdirs.user_data_dir(appname=appname, appauthor=appauthor, version=version, roaming=roaming)
        return self.PathType(path_str)

    def user_config_dir(self, appname=None, appauthor=None, version=None, roaming=False):
        path_str = appdirs.user_config_dir(appname=appname, appauthor=appauthor, version=version, roaming=roaming)
        return self.PathType(path_str)

    def site_config_dir(self, appname=None, appauthor=None, version=None):
        path_str = appdirs.site_config_dir(appname=appname, appauthor=appauthor, version=version, multipath=False)
        return self.PathType(path_str)

    def site_data_dir(self, appname=None, appauthor=None, version=None):
        path_str = appdirs.site_data_dir(appname=appname, appauthor=appauthor, version=version, multipath=False)
        return self.PathType(path_str)

    def user_cache_dir(self, appname=None, appauthor=None, version=None):
        path_str = appdirs.user_cache_dir(appname=appname, appauthor=appauthor, version=version)
        return self.PathType(path_str)

    def user_state_dir(self, appname=None, appauthor=None, version=None):
        path_str = appdirs.user_state_dir(appname=appname, appauthor=appauthor, version=version)
        return self.PathType(path_str)

    def user_log_dir(self, appname=None, appauthor=None, version=None):
        path_str = appdirs.user_log_dir(appname=appname, appauthor=appauthor, version=version)
        return self.PathType(path_str)
