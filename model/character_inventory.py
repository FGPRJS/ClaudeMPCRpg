from sqlmodel import SQLModel, Field


class CharacterInventory(SQLModel, table=True):
    __tablename__ = 'character_inventory'

    world_name: str = Field(primary_key=True)
    character_name: str = Field(primary_key=True)

    item_name: str = Field(primary_key=True)
    item_description: str = Field()
    item_count: int = Field()
