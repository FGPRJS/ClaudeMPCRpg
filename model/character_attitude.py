from sqlmodel import SQLModel, Field


class CharacterAttitude(SQLModel):
    __tablename__ = 'character_attitude'

    world_name: str = Field(primary_key=True)
    character_name: str = Field(primary_key=True)
    target_character_name: str = Field(primary_key=True)

    attitude: str = Field()