from pydantic import BaseModel


class UploadedImage(BaseModel):
    url: str


class ImageRead(BaseModel):
    src: str
    width: int
    height: int
    srcset: str = ""
    sizes: str = ""
