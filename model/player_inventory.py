from sqlmodel import SQLModel, Field


class PlayerInventory(SQLModel, table=True):
    __tablename__ = 'player_inventory'

    player_name: str = Field(primary_key=True)
    item_name: int = Field(primary_key=True)
    item_description: str = Field()
    item_count: int = Field(default=0)

