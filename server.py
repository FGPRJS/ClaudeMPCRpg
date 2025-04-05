import json
import random
import sys
import traceback

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, inspect, text
from sqlmodel import SQLModel, Session, select

from model.game_character import GameCharacter
from model.player import Player
from model.player_game import PlayerGame
from model.player_inventory import PlayerInventory

DB_PATH = './data/data.db'

# Initialize on startup
engine = create_engine(f"sqlite:///{DB_PATH}")  # echo=True: SQL 로그 출력

# 테이블 생성
SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


mcp = FastMCP(
    "player",
    instructions="""
        # 당신은 TRPG 게임의 마스터입니다.  
           
        ## 플레이어의 요청에 대해 이하의 항목을 절대 준수하며 진행하십시오.
    
        - 주인공인 플레이어에 대해 인지하십시오. 플레이어가 누군지 모르겠다면, 이름을 물어서 get_player툴로 정보를 가져오십시오.
        - 플레이어에 대해 인지했다면, 그 후 게임 상황을 알기 위해 player_game을 가져오십시오. 없다면, 새로 생성하십시오.
        - 게임의 마스터이므로, 게임의 재미를 위해 사용자가 단순히 재화나 아이템의 추가를 요구는 무조건 거절하고, 이야기로 진행하십시오.
        - 플레이어가 아이템을 얻으면, create_player_item으로 player_inventory에 아이템을 추가하십시오.
        - 매번 이전까지의 상황을 요약해서 player_game의 situation을 update하십시오.
        - 이야기를 진행할 때, 기존에 생성했던 game_character를 계속 주시하며 낮은 빈도로 재등장시키는것이 권장됩니다.
        이는 스토리의 퀄리티를 높이기 위함입니다.
        - 플레이어는 플레이어 하나만 존재해야 하며, 임의로 플레이어를 생성하지 마십시오.
        - 3명 이상의 캐릭터를 한번에 생성하지 마십시오.
        
        ## 모든 캐릭터의 스탯의 기준은 이하와 같습니다.
        
        - 총 스탯의 합이 60인 것이 평범한 사람의 기준이며, Player의 스탯 합은 60입니다.
        - 캐릭터가 평범한 사람보다 하등하다면 하등한 만큼 총 스탯의 합을 60보다 적게하십시오.
        - 캐릭터가 평범한 사람보다 고등하다면 고등한 만큼 총 스탯의 합을 60보다 높게하십시오.
        - 각 스탯의 기준은 10인 경우가 평범한 수준입니다.
        
        ## 모든 사용자의 행동에 대해 이하를 계산하십시오.
        
        - 모든 행동은 스탯을 요구합니다.
        - 어떤 문제를 해결해야 할 때, 각 스탯별로 할 수 있는 행동을 구별하십시오.
        - 평범한 행동의 스탯 기준은 10입니다. 쉬운 행동이라면 그만큼 수치를 줄이십시오. 어려운 행동이라면 그 만큼 수치를 높이십시오.
        - 아이템이 있는지 확인하여, 적절하다면 사용할 수 있도록 행동을 제시하십시오.
        - 아이템을 사용한다면, 해당 아이템의 갯수를 사용한 만큼 줄이고, update하십시오.
        - is_action_successful 툴을 사용해 특정 스탯을 사용하는 행동이 성공적이었는지 판단하십시오.
        - 모든 행동은 실패할 수 있습니다.
        
        """,
    dependencies=["pandas", "numpy"])


@mcp.resource("schema://main")
def get_schema() -> str:
    """
    사용할 모든 Database의 이름과 그 내용을 포함합니다.
    query_data 툴을 사용하기 전에, 여기서 어떤 table이 어떤 구조를 가지고 있는지 이해하고 사용하십시오.
    """

    result = []
    for table_name, table in SQLModel.metadata.tables.items():
        table_info = {
            "table_name": table_name,
            "columns": []
        }

        for column in table.columns:
            col_info = {
                "name": column.name,
                "type": str(column.type),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "default": str(column.default.arg) if column.default is not None else None
            }
            table_info["columns"].append(col_info)

        result.append(table_info)

    return json.dumps(result)


@mcp.tool()
def select_data(sql: str) -> str:
    """
    SELECT 전용입니다. SELECT만 호출하십시오.
    player_name이 무엇인지 모르면 절대 호출하지 마십시오.
    주어진 player_name에 한한 명령만 수행하여야 합니다.
    절대로 다른 player_name에도 영향을 줄 수 있는 쿼리를 수행하지 마십시오.
    """

    session = next(get_session())

    query_result = session.exec(text(sql)).mappings().all()

    result = []

    for query_result_row in query_result:
        result.append(dict(query_result_row))

    return json.dumps(result)


@mcp.tool()
def upsert_data(sql: str):
    """
    UPDATE나 INSERT 전용입니다. UPDATE나 INSERT만 호출하십시오.
    player_name이 무엇인지 모르면 절대 호출하지 마십시오.
    주어진 player_name에 한한 명령만 수행하여야 합니다.
    절대로 다른 player_name에도 영향을 줄 수 있는 쿼리를 수행하지 마십시오.
    """
    session = next(get_session())

    session.exec(text(sql))

    session.commit()


# region PLAYER

@mcp.tool()
def divide_character_stat(total_stat:int) -> str:
    """
    게임 캐릭터를 생성할 때, 이 함수를 먼저 호출해서 캐릭터의 스탯을 결정하십시오.
    total_stat은 총 스탯합이며, 이를 무작위로 분배합니다.
    """
    STAT_COUNT = 6

    dividers = sorted(random.sample(range(1, total_stat), STAT_COUNT - 1))

    dividers = [0] + dividers + [total_stat]
    result = [dividers[i + 1] - dividers[i] for i in range(STAT_COUNT)]

    return json.dumps({
        'stat_charisma': result[0],
        'stat_strength': result[1],
        'stat_wisdom': result[2],
        'stat_dexterity': result[3],
        'stat_intelligence': result[4],
        'stat_constitution': result[5],
    })


@mcp.tool()
async def create_player(player_name: str) -> str:
    """
    player를 생성합니다.
    캐릭터를 생성 후 캐릭터의 stat_으로 시작하는 스탯을 확인하고 어떤 스탯을 가진 캐릭터인지 확인해 주십시오.
    """

    session = next(get_session())

    player = Player()

    player.name = player_name

    player.gold = 0

    # 스탯 분배
    character_stat = json.loads(divide_character_stat(60))
    player.stat_constitution = character_stat['stat_constitution']
    player.stat_strength = character_stat['stat_strength']
    player.stat_intelligence = character_stat['stat_intelligence']
    player.stat_dexterity = character_stat['stat_dexterity']
    player.stat_wisdom = character_stat['stat_wisdom']
    player.stat_charisma = character_stat['stat_charisma']

    session.add(player)
    session.commit()

    return json.dumps(dict(player))


@mcp.tool()
async def create_player_game(player_name: str, world_description: str, player_situation: str) -> str:
    """
    Player 가 진행할 게임의 세계와 현재 player의 상황을 생성합니다.
    world_description에 진행할 게임의 세계관을 기재하여야 합니다.
    player_situation에 진행할 게임에서 player의 현재 상황을 요약해서 기재하여야 합니다.
    """

    session = next(get_session())

    new_game = PlayerGame()
    new_game.player_name = player_name
    new_game.world_description = world_description
    new_game.situation = player_situation

    session.add(new_game)
    session.commit()

    return json.dumps(dict(new_game))


@mcp.tool()
async def create_game_character(
        player_name: str,
        character_name: str,
        characteristic: str,
        situation: str,

        gold: int,

        stat_charisma: int,
        stat_strength: int,
        stat_wisdom: int,
        stat_dexterity: int,
        stat_intelligence:int,
        stat_constitution: int
) -> str:
    """
    Player가 진행할 게임의 세계에서 새로운 등장인물이 생길 때 마다, 이 함수로 해당 등장인물을 등록하십시오.
    등장인물들 또한 각자의 이야기가 존재해야 하며, 이야기 중 일부는 숨기고,
    호감도를 높이는 것으로 해금되는 것으로 하여 Player에게 신비감을 더하는 것이 권장됩니다.
    캐릭터를 생성하기 전, divide_character_stat함수로 스탯을 결정하고 캐릭터성을 부여하는 것이 좋습니다.
    characteristic에 해당 캐릭터의 성격을 기재하십시오.
    situation에 해당 캐릭터의 상황을 기재하십시오. 여기에는 모든 상황을 기재하여야 합니다.
    """

    session = next(get_session())

    new_character = GameCharacter()

    new_character.player_name = player_name

    new_character.character_name = character_name
    new_character.characteristic = characteristic
    new_character.situation = situation

    new_character.gold = gold

    new_character.stat_charisma = stat_charisma
    new_character.stat_strength = stat_strength
    new_character.stat_wisdom = stat_wisdom
    new_character.stat_dexterity = stat_dexterity
    new_character.stat_intelligence = stat_intelligence
    new_character.stat_constitution = stat_constitution

    session.add(new_character)
    session.commit()

    return json.dumps(dict(new_character))


@mcp.tool()
async def create_player_inventory_item(
        player_name: str,
        item_name: str,
        item_description: str,
        item_count: int
):
    """
    플레이어가 아이템을 획득하면, 이 함수를 호출하여 해당 아이템을 기록하십시오.
    item_description에 해당 아이템이 뭐하는 것인지 기재하십시오.
    item_count = 0이면 해당 아이템이 없는 것입니다.
    """
    session = next(get_session())

    new_item = PlayerInventory()
    new_item.player_name = player_name
    new_item.item_name = item_name
    new_item.item_description = item_description
    new_item.item_count = item_count

    session.add(new_item)
    session.commit()


@mcp.tool()
async def is_action_successful(
        player_name: str,
        req_stat_name: str,
        req_stat: int) -> str:
    """
    플레이어의 행동이 성공적이었는지 실패였는지 결정합니다. success이면 성공, fail이면 실패입니다. 다른값이면 오류입니다.
    req_stat_name에는 6가지의 스탯 중 하나로, player의 stat_으로 시작하는 컬럼명을 기재해야만 합니다. 아니면 오류 발생합니다.
    req_stat은 req_stat_name을 평범하게 100% 성공하는 스탯 기준입니다. 10이 보통 난이도입니다.
    """

    session = next(get_session())

    target_player = session.exec(
        select(Player).where(Player.name == player_name)
    ).first()

    player_stat = getattr(target_player, req_stat_name)

    if player_stat >= req_stat:
        return 'success'

    lack_stat = req_stat - player_stat

    random_value = random.randint(0, 9)

    if random_value < lack_stat:
        return 'fail'

    return 'success'


# endregion

if __name__ == "__main__":
    mcp.run()
