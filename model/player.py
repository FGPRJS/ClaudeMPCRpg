from sqlmodel import Field, SQLModel

from model.character import Character


class Player(Character, table=True):
    __tablename__ = 'player'

    name: str = Field(primary_key=True)

    gold: int = Field()