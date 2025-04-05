from sqlmodel import SQLModel, Field


class PlayerGame(SQLModel, table=True):
    __tablename__ = 'player_game'

    player_name: str = Field(primary_key=True)
    world_description: str = Field()
    situation: str = Field()

