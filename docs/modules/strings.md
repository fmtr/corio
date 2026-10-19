# strings
`from corio import strings`

String formatting and transform helpers.

## Truncation

`truncate` and `truncate_mid` flatten multiline text by default. Set `flatten_text=False` to preserve line breaks while limiting the string length.

When requesting a `Truncation` result with `return_type=Truncation`, use `was_truncated` to distinguish unchanged text from text that was shortened.

```python
from corio import strings

result = strings.truncate(
    "first line\nsecond line",
    length=12,
    flatten_text=False,
    return_type=strings.Truncation,
)

assert result.was_truncated is True
```
