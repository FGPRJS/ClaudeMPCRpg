from sqlmodel import SQLModel, Field


class Character(SQLModel):
    stat_strength: int = Field()
    stat_dexterity: int = Field()
    stat_constitution: int = Field()
    stat_intelligence: int = Field()
    stat_wisdom: int = Field()
    stat_charisma: int = Field()
