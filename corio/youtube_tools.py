from dataclasses import dataclass
from functools import cached_property
from pytubefix import YouTube, Stream, extract, request
from pytubefix.exceptions import RegexMatchError
from typing import AsyncIterator, Iterator
from urllib.error import HTTPError

from corio.path_tools.path_tools import Path

Stream = Stream


class Video(YouTube):
    """

    Video stub

    """


class AudioStreamDownloadError(Exception):
    """

    Error downloading audio stream

    """
    pass


@dataclass
class AudioStreamData:
    """

    Audio stream download data and progress information

    """
    message: str | None = None
    chunk: bytes | None = None
    percentage: int | None = None


class AudioStreamDownloader:
    """

    Download the highest-bitrate audio stream and write to temp directory.

    """

    def __init__(self, url_or_id: str):
        """

        Initialise with URL or video ID

        """

        try:
            self.id = extract.video_id(url_or_id)
        except RegexMatchError:
            self.id = url_or_id

        self.path = None

    @cached_property
    def url(self) -> str:
        """

        Get URL from ID

        """
        return f'https://youtube.com/watch?v={self.id}'

    async def download(self) -> AsyncIterator[AudioStreamData]:
        """

        Download the audio stream and yield chunks and progress information

        """

        yield AudioStreamData(message='Fetching video metadata...')
        video = Video(self.url)

        yield AudioStreamData('Finding audio streams...')

        audio_streams = video.streams.filter(only_audio=True).order_by('bitrate')
        if not audio_streams:
            raise AudioStreamDownloadError(f'Error downloading: no audio streams found in "{video.title}"')

        stream = audio_streams.last()
        yield AudioStreamData(f'Found highest-bitrate audio stream: {stream.audio_codec}/{stream.subtype}@{stream.abr}')

        self.path = Path.temp() / stream.default_filename
        if self.path.exists():
            self.path.unlink()

        if stream.filesize == 0:
            raise AudioStreamDownloadError(f'Error downloading: empty audio stream found in "{video.title}"')

        yield AudioStreamData('Downloading...')

        with self.path.open('wb') as out_file:
            for data in self.iter_data(stream):
                out_file.write(data.chunk)
                yield data

    def iter_data(self, stream: Stream, chunk_size: int | None = None) -> Iterator[AudioStreamData]:
        """

        Iterate over chunks of the specified size

        """
        bytes_total = bytes_remaining = stream.filesize

        if chunk_size:
            request.default_range_size = chunk_size

        try:
            stream = request.stream(stream.url)
        except HTTPError as e:
            if e.code != 404:
                raise
            stream = request.seq_stream(stream.url)

        for chunk in stream:
            bytes_remaining -= len(chunk)
            percentage = round(((bytes_total - bytes_remaining) / bytes_total) * 100)

            data = AudioStreamData(chunk=chunk, percentage=percentage)
            yield data
