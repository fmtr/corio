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
