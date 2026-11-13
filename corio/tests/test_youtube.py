from types import SimpleNamespace

import pytest

from corio import youtube


@pytest.mark.asyncio
async def test_download_handles_non_ascii_title_with_path_separator(tmp_path, monkeypatch):
    title = (
        "120min - Baby Fön Geräusch zum einschlafen | "
        "Haarfön für Babys / Hair Dryer Sleep Sounds"
    )
    stream = SimpleNamespace(
        title=title,
        default_filename=f"{title}.m4a",
        subtype="m4a",
        filesize=1,
        audio_codec="mp4a.40.2",
        abr="128kbps",
    )
    audio_streams = SimpleNamespace(last=lambda: stream)
    video = SimpleNamespace(
        streams=SimpleNamespace(
            filter=lambda **_: SimpleNamespace(order_by=lambda _: audio_streams)
        )
    )
    monkeypatch.setattr(youtube, "Video", lambda _: video)
    monkeypatch.setattr(youtube.Path, "temp", classmethod(lambda cls: cls(tmp_path)))

    downloader = youtube.AudioStreamDownloader("video-id")
    monkeypatch.setattr(
        downloader,
        "iter_data",
        lambda _: iter([youtube.AudioStreamData(chunk=b"audio")]),
    )

    async for _ in downloader.download():
        pass

    expected_filename = (
        "120min-baby-fön-geräusch-zum-einschlafen-"
        "haarfön-für-babys-hair-dryer-sleep-sounds.m4a"
    )
    assert downloader.path == tmp_path / expected_filename
    assert downloader.path.is_file()
