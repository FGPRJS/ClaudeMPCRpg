import random

from sqlalchemy import create_engine, text
from sqlmodel import SQLModel, Session, select

from model.player import Player

DB_PATH = './data/data.db'

# Initialize on startup
engine = create_engine(f"sqlite:///{DB_PATH}", echo=True)  # echo=True: SQL 로그 출력

# 테이블 생성
SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

session = next(get_session())

target_player = session.exec(
    select(Player).where(Player.name == '뉴뉴큥')
).first()

property_key: str = 'stat_strength'

player_stat = getattr(target_player, property_key)

if player_stat >= 15:
    print('성공')

lack_stat = 15 - player_stat

random_value = random.randint(0, 9)

if random_value < lack_stat:
    print('실패')

print('성공')