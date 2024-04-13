import os
import shutil
from pathlib import Path

from rembg import remove

import reflex as rx

UPLOAD_TYPES = {"image/png": [".png"], "image/jpeg": [".jpg", ".jpeg"]}


class State(rx.State):
    """The app state."""

    source: Path = Path("zebra.jpg")
    target: Path = Path("fixed_zebra.jpg")
    processing: bool = False

    async def init_client_folder(self):
        self._folder = Path(self.router.session.client_token)
        self._upload_path = rx.get_upload_dir() / self._folder

    async def on_upload(self, files: list[rx.UploadFile]):
        os.makedirs(self._upload_path, exist_ok=True)

        for image in files:
            self.source = self._folder / image.filename
            self.target = self._folder / f"fixed_{image.filename}"

            (rx.get_upload_dir() / self.source).write_bytes(await image.read())

            return State.remove_background()

    @rx.background
    async def remove_background(self):
        async with self:
            self.processing = True

        def remove_background():
            fixed = remove((rx.get_upload_dir() / self.source).read_bytes())
            (rx.get_upload_dir() / self.target).write_bytes(fixed)

        await rx._x.run_in_thread(remove_background)

        async with self:
            self.processing = False

    def clean_uploads(self):
        if self._upload_path.exists():
            shutil.rmtree(self._upload_path)
        self.source, self.target = "zebra.jpg", "fixed_zebra.jpg"


def remove_button():
    return rx.button(
        rx.icon("trash"), "Clear upload history", on_click=State.clean_uploads()
    )


def sidebar():
    return rx._x.layout.drawer_sidebar(
        rx.vstack(
            rx.markdown("# Clean history"),
            remove_button(),
            align="center",
            width="100%",
        )
    )


def image_header(*children):
    return rx.center(rx.text(*children))


def image_preview(image_path: str):
    return rx.scroll_area(
        rx.image(src=rx.get_upload_url(image_path), width=600), max_height="75vh"
    )


def display_original_image():
    return rx.upload(
        image_preview(State.source),
        accept=UPLOAD_TYPES,
        border="1px dashed var(--accent-12)",
        on_drop=State.on_upload(rx.upload_files()),
    )


def display_fixed_image():
    return rx.cond(
        State.processing, rx.center(rx.chakra.spinner()), image_preview(State.target)
    )


def grid_content():
    return rx.grid(
        image_header("Original Image ", rx.icon("image", display="inline")),
        image_header("Background Removed ", rx.icon("wrench", display="inline")),
        display_original_image(),
        display_fixed_image(),
        columns="2",
    )


@rx.page(route="/", title="Image Background Remover", on_load=State.init_client_folder)
def index() -> rx.Component:
    return sidebar(), rx.center(
        rx.vstack(
            rx.heading("Remove background from your image", size="7"),
            rx.markdown(
                "Try uploading an image to watch the background magically removed. Special thanks to the [rembg library](https://github.com/danielgatis/rembg)"
            ),
            grid_content(),
            rx.logo(),
        ),
        min_height="100vh",
    )


app = rx.App(theme=rx.theme(appearance="dark", accent_color="orange"))
