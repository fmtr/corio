from corio import strings


def test_is_format_string_handles_valid_and_invalid_masks():
    assert strings.is_format_string("hello {name}") is True
    assert strings.is_format_string("hello world") is False
    assert strings.is_format_string("hello {") is False


def test_format_data_formats_nested_collections():
    raw = {
        "{k}": "{v}",
        "items": ["{v}", "plain"],
    }
    actual = strings.format_data(raw, k="key", v="value")

    assert actual["key"] == "value"
    assert actual["items"] == ["value", "plain"]


def test_truncate_return_type_structured():
    actual = strings.truncate("abcdef", length=5, return_type=strings.Truncation)

    assert actual.text == "abcd…"
    assert actual.text_without_sep == "abcd"
    assert actual.remainder == "ef"


def test_truncate_mid_return_type_structured():
    actual = strings.truncate_mid("abcdefghij", length=7, return_type=strings.Truncation)

    assert actual.text == "abc…hij"
    assert actual.original == "abcdefghij"
    assert actual.text_without_sep is None


def test_join_natural_masks_and_empty():
    assert strings.join_natural([]) == "(None)"
    assert strings.join_natural(["a"]) == "a"
    assert strings.join_natural(["a", "b", "c"], mask='"{}"') == '"a", "b" and "c"'


def test_mask_supports_incremental_filling():
    mask = strings.Mask("Hello {name} from {place}")
    partial = mask.format(name="Ada")

    assert partial is mask
    assert str(mask) == "Hello Ada from {place}"
    assert mask.format(place="London") == "Hello Ada from London"


def test_get_docstring_trims_multiline_docstring():
    class Demo:
        """

        Demo docs.

        """

    assert strings.get_docstring(Demo) == "Demo docs."


def test_sanitize_and_camel_to_snake():
    assert strings.sanitize("Hello,", "World!", sep="-") == "hello-world"
    assert strings.camel_to_snake("HTTPRequestJSON") == "http_request_json"
