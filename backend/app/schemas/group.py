from pydantic import BaseModel, ConfigDict


class GroupBase(BaseModel):
    slug: str
    title: str


class GroupCreate(GroupBase):
    pass


class GroupRead(GroupBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
