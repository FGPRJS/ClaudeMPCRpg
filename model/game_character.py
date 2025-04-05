from sqlmodel import Field

from model.character import Character


class GameCharacter(Character, table=True):
    __tablename__ = 'game_character'

    player_name: str = Field(primary_key=True)

    gold: int = Field()

    character_name: str = Field(nullable=False)
    characteristic: str = Field()
    situation: str = Field()