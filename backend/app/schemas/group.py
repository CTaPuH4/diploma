from pydantic import BaseModel


class GroupBase(BaseModel):
    slug: str
    title: str


class GroupCreate(GroupBase):
    pass


class GroupRead(GroupBase):
    id: int

    class Config:
        from_attributes = True
