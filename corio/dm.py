import inspect
from cached_classproperty import cached_classproperty
from pydantic import BaseModel
from pydantic import RootModel, ConfigDict
from pydantic.fields import FieldInfo
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import PydanticUndefined, PydanticUndefinedType
from typing import ClassVar, List, Any, Dict
from typing_extensions import TypeForm

from corio.datatype import is_optional, none_else
from corio.iterator import get_class_lookup
from corio.strings import camel_to_snake
from corio.tools import Auto, Required, Empty


class Field(FieldInfo):
    """

    Allow DRYer field definitions, set annotation and defaults at the same time, easier field inheritance, etc.

    """
    NAME: ClassVar[type[Auto] | str | None] = Auto
    ANNOTATION: ClassVar[TypeForm[Any]] = Empty
    DEFAULT: ClassVar[Any] = Auto
    FILLS: ClassVar[dict[str, Any] | None] = None
    DESCRIPTION: ClassVar[str | None] = None
    TITLE: ClassVar[type[Auto] | str | None] = Auto
    SKIP_SCHEMA: ClassVar[bool] = False
    CONFIG: ClassVar[dict[str, Any] | None] = None

    def __init__(self, annotation=Empty, default=Empty, description=None, title=None, fills=None, skip_schema=None, **kwargs):
        """

        Infer default from type annotation, if enabled, use class/argument fills to create titles/descriptions, etc.

        """

        fills_super = getattr(super(), 'FILLS', None)
        self.fills = (fills_super or {}) | (self.FILLS or {}) | (fills or {})

        skip_schema = none_else(skip_schema, self.SKIP_SCHEMA)

        self.annotation = self.ANNOTATION if annotation is Empty else annotation
        if self.annotation is Empty:
            raise ValueError("Annotation must be specified.")

        if skip_schema:
            self.annotation = SkipJsonSchema[self.annotation]

        default = self.get_default_auto(default)
        if default is Required:
            default = PydanticUndefined

        description = self.get_desc(description)
        title = self.get_title_auto(title)
        kwargs |= (self.CONFIG or {})

        super().__init__(annotation=self.annotation, default=default, title=title, description=description, **kwargs)

    @cached_classproperty
    def name(cls) -> str:
        """

        Infer field name, if set to auto.

        """
        if cls.NAME is Auto:
            return camel_to_snake(cls.__name__)
        elif cls.NAME is None:
            return cls.__name__

        return cls.NAME

    def get_default_auto(self, default) -> type[Any] | None | PydanticUndefinedType:
        """

        Infer default, if not specified.

        """

        if default is not Empty:
            return default

        if self.DEFAULT is not Auto:
            return self.DEFAULT

        if is_optional(self.annotation):
            return None
        else:
            return Required

    def get_title_auto(self, mask) -> str | None:
        """

        Get title from classname/mask

        """

        if not mask:
            mask = self.__class__.__name__ if self.TITLE is Auto else self.TITLE

        if mask:
            return mask.format(**self.fills)

        return None

    def get_desc(self, mask) -> str | None:
        """

        Fill description mask, if specified

        """

        mask = mask or self.DESCRIPTION

        if mask:
            return mask.format(**self.fills)

        return None


def to_df(*objs, name_value='value'):
    """

    DataFrame representation of Data Models as rows.

    """
    from corio import tabular

    rows = []
    for obj in objs:
        if isinstance(obj, BaseModel):
            row = obj.model_dump()
        else:
            row = {name_value: obj}
        rows.append(row)

    df = tabular.DataFrame(rows)
    if 'id' in df.columns:
        df.set_index('id', inplace=True, drop=True)
    return df


class MixinArbitraryTypes:
    """

    Convenience for when non-serializable types are needed
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Base(BaseModel):
    """

    Base model allowing model definition via a list of custom Field objects.

    """
    model_config = ConfigDict(ignored_types=(cached_classproperty,))

    def run(self):
        """

        Behaviour when run as a CLI command, i.e. via Pydantic Settings. Run any subcommands then exit.

        """

        from pydantic_settings import get_subcommand

        command = get_subcommand(self, is_required=False, cli_exit_on_error=False)

        if not command:
            return

        result = command.run()
        if inspect.isawaitable(result):
            import asyncio
            result = asyncio.run(result)

        raise SystemExit(result)

    FIELDS: ClassVar[List[Field] | Dict[str, Field]] = []

    def __init_subclass__(cls, **kwargs):
        """

        Fetch aggregated fields metadata from the hierarchy and set annotations and FieldInfo objects in the class.

        """
        super().__init_subclass__(**kwargs)

        fields = {}
        for base in reversed(cls.__mro__):

            try:
                raw = base.FIELDS
            except AttributeError:
                raw = {}

            if isinstance(raw, dict):
                fields |= raw
            else:
                fields |= get_class_lookup(*raw, name_function=lambda cls_field: cls_field.name)

        cls.FIELDS = fields

        for name, field in fields.items():
            if name in cls.__annotations__:
                continue

            if inspect.isclass(field):
                field = field()

            setattr(cls, name, field)
            cls.__annotations__[name] = field.annotation

    def to_df(self, **kwargs):
        """

        DataFrame representation of Data Model.

        """
        from corio import tabular

        data = self.model_dump(**kwargs)
        df = tabular.pd.json_normalize(data, sep='_')
        return df

    @classmethod
    def to_df_empty(cls):
        """

        Empty DataFrame

        """
        from corio import tabular

        row = {name: None for name in cls.model_fields.keys()}
        df = tabular.pd.DataFrame([row])
        return df


class Root(RootModel):
    """

    Root (list) model

    """

    def to_df(self, **kwargs):
        """

        DataFrame representation with items as rows.

        """

        """

        DataFrame representation of Data Model.

        """
        from corio import tabular

        data = [item.model_dump(**kwargs) for item in self.items]
        dfs = [tabular.pd.json_normalize(datum, sep='_') for datum in data]
        df = tabular.pd.concat(dfs, axis=tabular.CONCAT_VERTICALLY)
        return df
