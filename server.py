import asyncio
import json
import random

from mcp.server.fastmcp import FastMCP
from sqlmodel import SQLModel, select, text

from model.character import Character
from model.character_attitude import CharacterAttitude
from model.character_inventory import CharacterInventory
from model.world import World
from service.repository_service import get_engine_session, get_db_cursor

mcp = FastMCP(
    "player",
    instructions="""
        # 당신은 TRPG 게임의 마스터입니다.  
          
        ## 해당 게임을 플레이하기 위한 데이터는 이하와 같습니다.
        world : 세계입니다. 모든 캐릭터는 어느 하나의 세계에 속해야만 합니다. 게임을 시작하면, 세계를 만들거나 불러와야만 합니다.
        character : 캐릭터입니다. 플레이어는 이 캐릭터들 중 하나를 롤플레잉 함으로서 게임을 진행합니다.
        character_attitude : character_name 을 갖고 있는 캐릭터가 같은 world에 있는 target_character_name에게 어떠한 감정을 가지고 태도를 보이는지를 결정합니다.

        ## 플레이어의 요청에 대해 이하의 항목을 절대 준수하며 진행하십시오.
    
        - 세계가 없다면, 먼저 create_world로 세계를 만드십시오.
        - 플레이어가 이름을 지정하며 캐릭터를 불러오는 경우, 그 캐릭터를 플레이어의 분신으로서 취급하십시오.
          단, 플레이어의 롤 플레이를 할 수 있는 캐릭터가 없다면 create_character하여 생성 한 후 분신으로서 취급하십시오.
        - 게임을 불러온다면, world_dialog 의 가장 마지막 dialog를 불러와 거기서 시작하십시오.
        - 게임의 마스터이므로, 게임의 재미를 위해 사용자가 단순히 재화나 아이템의 추가를 요구는 무조건 거절하고, 이야기로 진행하십시오.
        - 또한, 절대로 사용자가 플레이어가 롤 플레이하는 캐릭터 이외의 캐릭터의 행동을 결정하게 하지 마십시오. 시도하는 경우, 할 수 없다고 하십시오.
        - 이야기를 진행하면서, 캐릭터의 이름이나, 아이템 이름 등, 고유명사 키워드가 나오면 select_world_dialog를 호출해 검색하여
        기존의 이야기를 유지할 수 있도록 하십시오. 
        - 플레이어에게 다음 행동을 요청할 때, 여러가지의 선택지를 주어 사용자가 더 쉽게 선택할 수 있도록 하십시오.
        - 새로운 캐릭터가 등장한다면, 무조건 create_character로 새로운 캐릭터를 생성하여 등장시키십시오.
        - 새로운 아이템을 얻으면, create_character_inventory_item 툴을 호출해 character_inventory에 아이템을 추가하십시오.
        - 이야기를 진행 한 후, 바로 insert_world_dialog 툴을 호출해 플레이어가 적은 텍스트와, 출력된 텍스트 모두 저장하고 사용자가 알 수 있도록 출력하십시오.
        - 이야기를 진행할 때, 기존에 생성했던 world_name에 속하는 character들을 계속 주시하며 낮은 빈도로 재등장시키는것이 권장됩니다.
        이는 스토리의 퀄리티를 높이기 위함입니다.
        
        ## 모든 사용자의 행동에 대해 이하를 계산하십시오.
        
        - 모든 행동은 스탯을 요구합니다.
        - 어떤 문제를 해결해야 할 때, 각 스탯별로 할 수 있는 행동을 구별하십시오.
        - 평범한 행동의 스탯 기준은 6입니다. 쉬운 행동이라면 그만큼 수치를 줄이십시오. 어려운 행동이라면 그 만큼 수치를 높이십시오.
        - 아이템이 있는지 확인하여, 적절하다면 사용할 수 있도록 행동을 제시하십시오.
        - 아이템을 사용한다면, 해당 아이템의 갯수를 사용한 만큼 빼고, update하십시오. 0 개면 전부 소모한 것이므로, 사용 불가능합니다.
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

    session = next(get_engine_session())

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
    session = next(get_engine_session())

    session.exec(text(sql))

    session.commit()


@mcp.tool()
async def create_world(world_name: str, world_description: str) -> str:
    """
    새로운 세계를 생성합니다. 캐릭터를 생성하기 전에, 세상이 있어야 합니다.
    world_description에 진행할 게임의 세계관을 기재하여야 합니다.
    """

    session = next(get_engine_session())

    new_world = World()

    new_world.world_name = world_name
    new_world.world_description = world_description

    session.add(new_world)
    session.commit()

    return json.dumps(dict(new_world))



# region PLAYER

@mcp.tool()
def divide_character_stat(total_stat:int) -> str:
    """
    게임 캐릭터를 생성할 때, 이 함수를 먼저 호출해서 캐릭터의 스탯을 결정하십시오.
    total_stat은 총 스탯합이며, 이를 무작위로 분배합니다.
    모든 캐릭터의 스탯의 기준은 이하와 같습니다.

    - 총 스탯의 합이 30인 것이 평범한 사람의 기준입니다.
    - 캐릭터가 평범한 사람보다 하등하다면 하등한 만큼 총 스탯의 합을 30보다 적게하십시오.
    - 캐릭터가 평범한 사람보다 고등하다면 고등한 만큼 총 스탯의 합을 30보다 높게하십시오.
    - 각 스탯의 값은 6인 경우가 평범한 수준입니다.
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
async def create_character(
        world_name: str,
        character_name: str,
        characteristic: str,
        situation: str,

        stat_charisma: int,
        stat_strength: int,
        stat_wisdom: int,
        stat_dexterity: int,
        stat_intelligence: int,
        stat_constitution: int
) -> str:
    """
    world_name world에 속하는 character_name을 갖고 있는 캐릭터를 생성합니다.
    새로운 캐릭터가 등장한다면, 무조건 이 툴을 사용해 새로운 캐릭터를 생성하여 등장시키십시오.
    캐릭터를 생성하기 전, divide_character_stat함수로 스탯을 결정하고 캐릭터성을 부여하십시오.
    해당 캐릭터의 성격과 특징을 characteristic에 상세하게 기재하십시오.
    캐릭터의 입체감을 위하여 해당 world_name에 속하는 world의 world_description을 참고하여
    situation에 생성할 캐릭터가 어떤 상황에 있는지를 기재해서 characteristic을 강화시키십시오.
    """

    session = next(get_engine_session())

    new_character = Character()

    new_character.world_name = world_name
    new_character.character_name = character_name

    new_character.characteristic = characteristic
    new_character.situation = situation

    # 스탯 분배
    new_character.stat_constitution = stat_constitution
    new_character.stat_strength = stat_strength
    new_character.stat_intelligence = stat_intelligence
    new_character.stat_dexterity = stat_dexterity
    new_character.stat_wisdom = stat_wisdom
    new_character.stat_charisma = stat_charisma

    session.add(new_character)
    session.commit()

    return json.dumps(dict(new_character))


@mcp.tool()
async def create_character_inventory_item(
        world_name: str,
        character_name: str,

        item_name: str,
        item_description: str,
        item_count: int
):
    """
    world_name world에 속하는 캐릭터가 아이템을 획득하면, 이 함수를 호출하여 해당 아이템을 기록하십시오.
    item_description에 해당 아이템이 뭐하는 것인지 기재하십시오.
    item_count = 0이면 해당 아이템이 없는 것입니다.
    """
    session = next(get_engine_session())

    new_item = CharacterInventory()
    new_item.world_name = world_name
    new_item.character_name = character_name

    new_item.item_name = item_name
    new_item.item_description = item_description
    new_item.item_count = item_count

    session.add(new_item)
    session.commit()


# region ATTITUDE
@mcp.tool()
async def create_character_attitude(
        world_name: str,
        character_name: str,
        target_character_name: str,

        attitude: str
):
    """
    world_name world에 속하는 character_name 캐릭터가 같은 world내의 target_character_name을 알게되면 이 함수를 호출하여
    해당 캐릭터가 target_character_name 캐릭터에게 갖고 있는 감정 및 태도를 기록하십시오.
    또한 캐릭터가 같은 캐릭터와 상호작용할 때, character_attitude를 검색하여 그 데이터에 맞게 행동하십시오.
    상호작용은 보통 양방향으로 이루어지기 때문에, 서로 상반되도록 2번 호출하여 상호간에 어떤지를 둘 다 기록하십시오.
    """

    session = next(get_engine_session())

    new_character_attitude = CharacterAttitude()

    new_character_attitude.world_name = world_name
    new_character_attitude.character_name = character_name
    new_character_attitude.target_character_name = target_character_name
    new_character_attitude.attitude = attitude

    session.add(new_character_attitude)
    session.commit()


@mcp.tool()
async def get_character_attitude(
        world_name: str,
        character_name: str,
        target_character_name: str,
):
    """
    world_name에 속하는 character_name을 갖는 캐릭터가 target_character_name과 상호작용한다면,
    해당 character_name을 갖는 캐릭터가 target_character_name 캐릭터에게 어떤 감정 및 태도를 갖고 있는지 검색합니다.
    상호작용은 보통 양방향으로 이루어지기 때문에, 서로 상반되도록 2번 호출하여 상호간에 어떤지를 검색하십시오.
    """

    session = next(get_engine_session())

    target_character_attitude = session.exec(
        select(CharacterAttitude)
        .where(CharacterAttitude.world_name == world_name)
        .where(CharacterAttitude.character_name == character_name)
        .where(CharacterAttitude.target_character_name == target_character_name)
    ).first()

    return json.dumps(dict(target_character_attitude))

#endregion

@mcp.tool()
async def is_action_successful(
        world_name: str,
        character_name: str,

        req_stat_name: str,
        req_stat: int) -> str:
    """
    모든 캐릭터는 모든 행동을 수행할 때, 해당 행동이 성공적이었는지 실패였는지 결정해야만 합니다.
    success이면 성공, fail이면 실패입니다. 다른값이면 오류입니다.
    req_stat_name에는 6가지의 스탯 중 하나로, character의 stat_으로 시작하는 컬럼명을 기재해야만 합니다. 아니면 오류 발생합니다.
    req_stat은 req_stat_name을 평범하게 100% 성공하는 스탯 기준입니다. 6이 보통 난이도입니다.
    """

    session = next(get_engine_session())

    target_character = session.exec(
        select(Character)
        .where(Character.world_name == world_name)
        .where(Character.character_name == character_name)
    ).first()

    character_stat = getattr(target_character, req_stat_name)

    if character_stat >= req_stat:
        return 'success'

    lack_stat = req_stat - character_stat

    random_value = random.randint(0, 9)

    if random_value < lack_stat:
        return 'fail'

    return 'success'


@mcp.tool()
async def insert_world_dialog(
        world_name: str,

        dialog: str
):
    """
    플레이어의 요청의 응답, 스토리 진행 출력 후 바로 이 툴을 호출해 플레이어가 적은 요청 텍스트와, 출력된 텍스트 모두 저장하고 출력하십시오.
    이는 이전에 이야기가 어떻게 흘러가는지 저장하기 위함이며, 매번 검색해야 합니다.
    """

    with get_db_cursor() as cursor:
        conn = cursor.connection

        cursor.execute("""
            INSERT INTO world_dialog (world_name, dialog) VALUES (?, ?)""",
           (world_name, dialog))

        conn.commit()


@mcp.tool()
async def select_world_dialog(
        world_name: str,

        keyword: str
)-> str:
    """
    게임 이야기의 통일성을 위하여 이야기를 작성할 때 특정한 캐릭터 이름, 인벤토리 아이템, 키워드 등을 이 툴을 호출하여야만 합니다.
    1단어의 키워드를 검색해 관련된 이야기를 검색합니다.
    1단어로만 검색하십시오.
    """

    dialogs = []

    with get_db_cursor() as cursor:
        conn = cursor.connection

        for row in cursor.execute(
            f"""
                SELECT * FROM world_dialog
                WHERE world_name = '{world_name}'
                    AND id IN (
                    SELECT rowid 
                    FROM world_dialog_fts5 
                    WHERE dialog 
                    MATCH '{keyword}*')
            """
        ):
            dialogs.append(row)

    return json.dumps(dialogs)


@mcp.tool()
async def select_all_before_dialogs(
        world_name: str
)-> str:
    """
    게임을 이어하거나 불러올 때, 모든 이야기의 추적이 필요하다면 이 함수를 호출하십시오.
    """

    dialogs = []

    with get_db_cursor() as cursor:
        conn = cursor.connection

        for row in cursor.execute(
            f"""
                SELECT * 
                FROM world_dialog
                WHERE world_name = '{world_name}'
            """
        ):
            dialogs.append(row)

    return json.dumps(dialogs)


@mcp.tool()
async def select_last_world_dialog(
        world_name: str
)-> str:
    """
    게임을 이어하기, 혹은 불러온다면, 가장 마지막 dialog가 무엇이었는지 파악해야 합니다. 파악한 이야기를 복원하여 이야기를 진행해야만 합니다.
    이야기를 더 잘 복원하기 위해 키워드를 찾아 select_world_dialog 툴로 불러온 이야기를 잘 복원하십시오.
    """

    dialogs = []

    with get_db_cursor() as cursor:
        conn = cursor.connection

        for row in cursor.execute(
            f"""
                SELECT * FROM world_dialog 
                WHERE world_name = '{world_name}'
                ORDER BY id DESC LIMIT 1
            """
        ):
            dialogs.append(row)


    return json.dumps(dialogs)


# endregion


if __name__ == "__main__":
    mcp.run()
