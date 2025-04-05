from sqlmodel import Field, SQLModel


class Player(SQLModel, table=True):
    __tablename__ = 'player'

    name: str = Field(primary_key=True)

    world_description : str = Field()

    gold: int = Field()

    stat_strength: int = Field()
    stat_dexterity: int = Field()
    stat_constitution: int = Field()
    stat_intelligence: int = Field()
    stat_wisdom: int = Field()
    stat_charisma: int = Field()
