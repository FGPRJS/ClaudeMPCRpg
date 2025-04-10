from sqlmodel import SQLModel, Field


class World(SQLModel, table=True):
    __tablename__ = 'world'

    world_name: str = Field(primary_key=True)

    world_description: str = Field()

