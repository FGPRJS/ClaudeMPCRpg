from sqlalchemy import create_engine, text
from sqlmodel import SQLModel, Session

DB_PATH = './data/data.db'

# Initialize on startup
engine = create_engine(f"sqlite:///{DB_PATH}", echo=True)  # echo=True: SQL 로그 출력

# 테이블 생성
SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

session = next(get_session())

session.exec(text("UPDATE player SET gold = 1000 WHERE name = '뉴뉴큥'"))

session.commit()

print('완료')