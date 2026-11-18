import flet as ft

from corio import function, interface


class SampleApp(interface.Base[interface.Context]):
    @function.ccp
    def metadata(cls) -> interface.Metadata:
        """

        Return the sample app's manifest metadata.

        """
        return interface.Metadata(
            name="Sample Studio",
            short_name="Studio",
            description="An example Flet web application.",
            theme_color="#224466",
            background_color="#F0F2F4",
        )

    def __init__(self):
        super().__init__(controls=[ft.Text(self.metadata.name)])


if __name__ == "__main__":
    SampleApp.launch()
