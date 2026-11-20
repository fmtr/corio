import pytest

from corio.hook import ImportHook, MissingExtraError, MissingExtraMockModule


def test_missing_extra_mock_module_raises_with_context():
    mock_module = MissingExtraMockModule("path.app", ModuleNotFoundError("no appdirs"))

    with pytest.raises(MissingExtraError):
        mock_module()

    with pytest.raises(MissingExtraError):
        _ = mock_module.any_attr


def test_import_hook_translates_module_not_found_for_corio_callers():
    hook = ImportHook(auto_register=False)

    def fake_import(*_args, **_kwargs):
        raise ModuleNotFoundError("missing dep")

    hook._previous_import = fake_import

    with pytest.raises(MissingExtraError):
        hook("missing", globals={"__name__": "corio.path.app"})

    with pytest.raises(ModuleNotFoundError):
        hook("missing", globals={"__name__": "external.module"})
