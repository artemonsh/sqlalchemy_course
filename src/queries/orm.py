from sqlalchemy import text, insert, inspect
from database import sync_engine, async_engine, session_factory, async_session_factory, Base
from models import WorkersOrm


def create_tables():
    sync_engine.echo = True
    Base.metadata.drop_all(sync_engine)
    Base.metadata.create_all(sync_engine)
    sync_engine.echo = True

# Асинхронный вариант, не показанный в видео
async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def insert_data():
    with session_factory() as session:
        worker_jack = WorkersOrm(username="Jack")
        worker_michael = WorkersOrm(username="Michael")
        session.add_all([worker_jack, worker_michael])
        session.commit()

async def insert_data():
    async with async_session_factory() as session:
        worker_jack = WorkersOrm(username="Jack")
        worker_michael = WorkersOrm(username="Michael")
        session.add_all([worker_jack, worker_michael])
        await session.commit()
