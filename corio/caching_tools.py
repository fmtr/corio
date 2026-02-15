import cachetools
from datetime import timedelta, datetime
from diskcache import Cache

from fmtr.tools.constants import Constants
from fmtr.tools.logging_tools import logger
from fmtr.tools.path_tools.path_tools import Path


class Dump(dict):
    """

    Subclass `dict` to distinguish between dumped sub-caches and regular dictionaries.

    """

class Disk(Cache):
    """

    Subclass of `diskcache` Cache that implements nested/structured caches

    """

    ROOT_KEY = '__root__'

    def __init__(self, path=None, is_root=True, **settings):
        """

        Read in existing cache structure from filesystem.

        """

        path = Path(path)
        if is_root:
            if not path.parent.exists():
                raise FileNotFoundError(f"Directory {path.parent=} does not exist")
            if path and not path.exists():
                logger.warning(f'Cache does not exist. Will be created. {str(path)=}...')

            logger.info(f'Initializing Disk Cache {str(path)=}...')

        super().__init__(directory=str(path / self.ROOT_KEY), **settings)

        self.path = path
        self.children = {}

        for path_dir in self.path.iterdir():
            if path_dir.stem == self.ROOT_KEY:
                continue
            if path_dir.is_dir():
                self.create(path_dir.name)

    def create(self, key):
        if key in self.children:
            raise KeyError(f'Sub-cache for key "{key}" already exists')
        if key in self:
            raise KeyError(f'Data for key "{key}" already exists: {repr(self[key])}')

        self.children[key] = self.__class__(self.path / key, is_root=False)

    def __getitem__(self, key):
        if key in self.children:
            return self.children[key]
        else:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        if value is type(self):
            self.create(key)
        else:
            super().__setitem__(key, value)

    def setdefault(self, key, default):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return self[key]

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.path}")'

    def items(self):
        for key in self:
            yield key, self[key]

    def dump(self):
        data = Dump(self.items())
        for key, child in self.children.items():
            data[key] = child.dump()
        return data

    def iterkeys(self):
        yield from self.children.keys()
        yield from super().iterkeys()

    @property
    def data(self):
        return self.dump()


class TLRU(cachetools.TLRUCache):
    """

    Subclass to include logging and simplify global TTU

    """
    MASK_MAPPING = '{key} ' + Constants.ARROW + ' {value}'

    def __init__(self, maxsize=1_024, timer=datetime.now, getsizeof=None, ttu_static=None, desc=None):
        """

        Add overridable TTU method

        """
        super().__init__(maxsize=maxsize, ttu=self.get_ttu, timer=timer, getsizeof=getsizeof)
        self.ttu_static = ttu_static
        self.desc = desc

    @property
    def cache_desc(self):
        """

        Friendly description of cache

        """
        desc = self.desc or self.__class__.__name__
        return desc

    def get_ttu(self, _key, value, now) -> float | timedelta:
        """

        Default implementation just adds on the static TTU

        """
        return now + self.ttu_static

    def expire(self, time=None):
        """

        Log expiry

        """
        items = super().expire(time)
        if not items:
            return items

        with logger.span(f'{self.desc} cache expiry {len(items)=}...'):
            for key, value in items:
                logger.debug(self.MASK_MAPPING.format(key=key, value=value))

        return items

    def popitem(self):
        """

        Log eviction

        """
        key, value = super().popitem()
        logger.debug(f'{self.desc} cache eviction: {self.MASK_MAPPING.format(key=key, value=value)}')
        return key, value

    def dump(self):
        """

        Dump contents

        """
        data = Dump(self.items())
        return data

    @property
    def data(self):
        """

        Dump as property

        """
        return self.dump()



if __name__ == '__main__':
    sec10 = timedelta(seconds=10)
    c = TLRU(ttu_static=sec10, maxsize=2, desc='Test Data')
    c['test'] = 'val'
    c['test2'] = 'val2'
    c['test3'] = 'val3'
    c






    path_tmp_cache = Path.cwd().parent.parent / 'data' / 'cache'
    tc = Disk(path_tmp_cache)

    tc.setdefault('c', Disk).setdefault('c1', Disk)['subkey'] = 0000.1
    # tc['c']=Disk.Create
    tc['c']['test'] = False
    tc['val'] = 123
    tc.setdefault('b', Disk)
    tc.setdefault('a', Disk)
    tc['a']['value2'] = 456
    tc['a']['value4'] = dict(mykey='myvalue')

    tc['b']['value3'] = [789, True]
    tc.dump()
    {}.items()
