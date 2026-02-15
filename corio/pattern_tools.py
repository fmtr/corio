import regex as re
from dataclasses import dataclass, asdict
from fmtr.tools import Constants
from fmtr.tools.logging_tools import logger
from fmtr.tools.string_tools import join
from functools import cached_property
from typing import List, Any


class RewriteCircularLoopError(Exception):
    """

    Circular loop error

    """


MASK_GROUP = '(?:{pattern})'
MASK_NAMED = r"(?P<{key}>{pattern})"


def alt(*patterns):
    patterns = sorted(patterns, key=len, reverse=True)
    pattern = '|'.join(patterns)
    pattern = MASK_GROUP.format(pattern=pattern)
    return pattern

@dataclass
class Key:
    RECORD_SEP = '␞'
    FILLS = None

    def flatten(self, data):
        """

        Flatten/serialise dictionary data

        """
        pairs = [f'{value}' for key, value in data.items()]
        string = self.RECORD_SEP.join(pairs)
        return string

    @cached_property
    def pattern(self):
        """

        Serialise to pattern

        """
        data = {
            key:
                MASK_NAMED.format(
                    key=key,
                    pattern=value.format_map(self.fills))
            for key, value in asdict(self).items()
        }
        pattern = self.flatten(data)
        return pattern

    @cached_property
    def rx(self):
        """

        Compile to Regular Expression

        """
        return re.compile(self.pattern)

    @cached_property
    def string(self):
        """

        Serialise to string

        """
        string = self.flatten(asdict(self))
        return string

    @cached_property
    def fills(self):
        """

        Add key names as regex group names

        """
        return {key: MASK_NAMED.format(key=key, pattern=value) for key, value in self.FILLS.items()}


    def transform(self, match: re.Match):
        """

        Transform match object into a new object of the same type.

        """
        fills = match.groupdict()
        data = {key: value.format_map(fills) for key, value in asdict(self).items()}
        obj = self.__class__(**data)
        return obj


@dataclass
class Item:
    """

    Key-value pair

    """
    source: Key
    target: Key


@dataclass(kw_only=True)
class Transformer:
    """
    
    Pattern-based, dictionary-like mapper.
    Compiles an complex set of rules into single regex pattern, and determines which rule matched.
    Inputs are then transformed according to the matching rule.
    Works like a pattern-based dictionary when is_recursive==False.
    Works something like an FSA/transducer when is_recursive=True.

    """
    PREFIX_GROUP = '__'
    items: List[Item]
    default: Any = None
    is_recursive: bool = False

    def __post_init__(self):
        """

        Compile on init

        """
        return self.compile(clear=False)

    def compile(self, clear=True):
        """

        Re/compile regex pattern, invalidating existing caches if recompile.

        """
        if clear:
            del self.pattern
            del self.rx

        with logger.span(f'Compiling expression {len(self.items)=}'):
            rx = self.rx
        logger.debug(f'Compiled successfully {rx.groups=}')

    @cached_property
    def pattern(self) -> str:
        """
        
        Dynamically generated regex pattern based on the rules provided.

        """
        patterns = [
            MASK_NAMED.format(key=f'{self.PREFIX_GROUP}{i}', pattern=item.source.pattern)
            for i, item in enumerate(self.items)
        ]
        pattern = alt(*patterns)
        return pattern

    @cached_property
    def rx(self) -> re.Pattern:
        """

        Regex object.

        """
        return re.compile(self.pattern)

    def get_default(self, key: Key) -> Any:
        """

        Define what to return in case of no match

        """
        if self.is_recursive:
            return key
        else:
            return self.default

    def get(self, key: Key) -> Key | Any:
        """

        Use recursive or single lookup pass, depending on whether recursive lookups have been specified.

        """
        if self.is_recursive:
            with logger.span(f'Transforming recursively {key=}...'):
                return self.get_recursive(key)
        else:
            with logger.span(f'Transforming linearly {key=}...'):
                return self.get_one(key)

    def get_one(self, key: Key) -> Key | Any:
        """

        Single lookup pass.
        Lookup the source string based on the matching rule.

        """

        match = self.rx.fullmatch(key.string)

        if not match:
            value = self.get_default(key)
            logger.debug(f'No match for {key=}. Returning {self.get_default(key)=}')
        else:

            match_ids = {name: v for name, v in match.groupdict().items() if v}
            rule_ids = {
                int(id.removeprefix(self.PREFIX_GROUP))
                for id in match_ids.keys() if id.startswith(self.PREFIX_GROUP)
            }

            if len(rule_ids) != 1:
                msg = f'Multiple group matches: {rule_ids}'
                raise ValueError(msg)

            rule_id = next(iter(rule_ids))
            rule = self.items[rule_id]

            logger.debug(f'Matched using {rule_id=}: {rule.source=}')

            if isinstance(rule.target, Key):
                value = rule.target.transform(match)
            else:
                value = rule.target

            logger.debug(f'Transformed using {rule_id=}: {key=} → {value=}')

        return value

    def get_recursive(self, key: Key) -> Key | Any:
        """

        Lookup the provided key by continuously applying transforms until no changes are made
        or a circular loop is detected.

        """
        history = []
        previous = key

        def get_history_str():
            return join(history, sep=Constants.ARROW_SEP)

        while True:
            if previous in history:
                history.append(previous)
                msg = f'Loop detected on node "{previous}": {get_history_str()}'
                raise RewriteCircularLoopError(msg)

            history.append(previous)
            new = previous
            new = self.get_one(new)
            if new == previous:
                break
            previous = new

            if not isinstance(new, Key):
                history.append(previous)
                break

        if len(history) == 1:
            history_str = 'No transforms performed.'
        else:
            history_str = get_history_str()
        logger.debug(f'Finished transforming: {history_str}')

        return previous


if __name__ == '__main__':
    ...
