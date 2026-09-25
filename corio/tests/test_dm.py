from cached_classproperty import cached_classproperty

from corio import dm


def test_base_ignores_cached_class_properties():
    class Model(dm.Base):
        value: str

        @cached_classproperty
        def label(cls) -> str:
            return cls.__name__

    assert Model.model_fields.keys() == {"value"}
    assert Model.label == "Model"


def test_base_run_can_be_overridden_by_a_tool():
    class Model(dm.Base):
        def run(self):
            return "ran"

    assert Model().run() == "ran"


def test_field_name_is_inferred_from_class_name():
    class UserName(dm.Field):
        ANNOTATION = str

    assert UserName.name == "user_name"


def test_field_name_can_be_explicit():
    class UserName(dm.Field):
        NAME = "display_name"
        ANNOTATION = str

    assert UserName.name == "display_name"


def test_base_uses_field_name_property():
    class UserName(dm.Field):
        ANNOTATION = str

    class Model(dm.Base):
        FIELDS = [UserName]

    assert Model.model_fields.keys() == {"user_name"}
