from sqlmodel import SQLModel, Field


class Character(SQLModel, table=True):
    __tablename__ = 'character'

    world_name: str = Field(primary_key=True)
    character_name: str = Field(primary_key=True, nullable=False)

    characteristic: str = Field()
    situation: str = Field()

    stat_strength: int = Field()
    stat_dexterity: int = Field()
    stat_constitution: int = Field()
    stat_intelligence: int = Field()
    stat_wisdom: int = Field()
    stat_charisma: int = Field()
