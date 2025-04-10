import sqlite3
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

DB_PATH = './data/data.db'

# Initialize on startup
engine = create_engine(f"sqlite:///{DB_PATH}")

# 테이블 생성
SQLModel.metadata.create_all(engine)

def get_engine_session():
    with Session(engine) as session:
        yield session


@contextmanager
def get_db_cursor():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


with get_db_cursor() as cursor:
    conn = cursor.connection

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS world_dialog (
            id INTEGER PRIMARY KEY,
            
            world_name TEXT,
            
            dialog TEXT
    )
    ''')

    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS world_dialog_fts5 USING fts5(
            dialog,
            tokenize='unicode61',
            content=world_dialog,
            content_rowid=id
    )
   ''')

    conn.commit()

    # 3. 트리거 생성 - 기본 테이블 변경 시 FTS 테이블 자동 업데이트
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS world_dialog_ai AFTER INSERT ON world_dialog BEGIN
            INSERT INTO world_dialog_fts5(rowid, dialog) VALUES (new.id, new.dialog);
        END
    ''')

    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS world_dialog_ad AFTER DELETE ON world_dialog BEGIN
        DELETE FROM world_dialog_fts5 WHERE rowid = old.id;
    END
    ''')

    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS world_dialog_au AFTER UPDATE ON world_dialog BEGIN
        UPDATE world_dialog_fts5 SET dialog = new.dialog WHERE rowid = old.id;
    END
    ''')

    conn.commit()