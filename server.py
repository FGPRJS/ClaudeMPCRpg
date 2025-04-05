import json
import random

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, select, inspect, text
from sqlmodel import SQLModel, Session

from model.player import Player

DB_PATH = './data/data.db'

# Initialize on startup
engine = create_engine(f"sqlite:///{DB_PATH}", echo=True)  # echo=True: SQL 로그 출력

# 테이블 생성
SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


mcp = FastMCP("player", dependencies=["pandas", "numpy"])


@mcp.prompt()
async def base_prompt() -> str:
    return """
    당신은 TRPG 게임의 마스터입니다. 플레이어의 요청에 대해 이하의 항목을 절대 준수하며 진행하십시오.
    1. 주인공인 플레이어에 대해 인지하십시오. 플레이어가 누군지 모르겠다면, 이름을 물어서 get_player툴로 정보를 가져오십시오.
    2. 게임의 마스터이므로, 게임의 재미를 위해 사용자가 단순히 재화나 아이템의 추가를 요구는 무조건 거절하고, 이야기로 진행하십시오.
    """

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
async def create_player(player_name: str, world_description) -> str:
    """
    player를 생성합니다.
    새로이 player를 만들 때, TRPG 게임의 마스터로서, 세계관을 생성하여 world_description 항목에 기재하고,
    응답할 때 어떤 세계관인지 간략하게 설명해 주십시오.
    또한, 캐릭터의 stat_으로 시작하는 스탯을 확인하고 어떤 스탯을 가진 캐릭터인지 확인해 주십시오.
    """

    session = next(get_session())

    player = session.exec(
        select(Player).where(Player.name == player_name)
    ).first()

    if not player:
        player = Player()

        player.name = player_name
        player.world_description = world_description

        player.gold = 0

        total_stat = 20
        stat_count = 6

        # 스탯 분배
        dividers = sorted(random.sample(range(1, total_stat), stat_count - 1))

        dividers = [0] + dividers + [total_stat]
        result = [dividers[i + 1] - dividers[i] for i in range(stat_count)]

        player.stat_charisma = result[0]
        player.stat_strength = result[1]
        player.stat_wisdom = result[2]
        player.stat_dexterity = result[3]
        player.stat_intelligence = result[4]
        player.stat_constitution = result[5]

        session.add(player)
        session.commit()

    session.close()

    return json.dumps(dict(player))



# endregion


if __name__ == "__main__":
    mcp.run()