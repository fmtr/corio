from inspect import stack


def get_call_path(offset=1):
    """

    Get the path of the calling module

    """
    from fmtr.tools.path_tools import Path
    frames = stack()
    frame_called = frames[offset]
    path = Path(frame_called.filename).absolute()
    return path
