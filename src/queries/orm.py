from sqlalchemy import Integer, and_, cast, func, insert, inspect, or_, select, text
from sqlalchemy.orm import aliased, contains_eager, joinedload, selectinload

from database import Base, async_engine, async_session_factory, session_factory, sync_engine
from models import ResumesOrm, VacanciesOrm, WorkersOrm, Workload
from schemas import (
    ResumesRelVacanciesRepliedDTO,
    ResumesRelVacanciesRepliedWithoutVacancyCompensationDTO,
    WorkersRelDTO,
)


class SyncORM:
    @staticmethod
    def create_tables():
        sync_engine.echo = False
        Base.metadata.drop_all(sync_engine)
        Base.metadata.create_all(sync_engine)
        sync_engine.echo = True

    @staticmethod
    def insert_workers():
        with session_factory() as session:
            worker_jack = WorkersOrm(username="Jack")
            worker_michael = WorkersOrm(username="Michael")
            session.add_all([worker_jack, worker_michael])
            # flush отправляет запрос в базу данных
            # После flush каждый из работников получает первичный ключ id, который отдала БД
            session.flush()
            session.commit()

    @staticmethod
    def select_workers():
        with session_factory() as session:
            query = select(WorkersOrm)
            result = session.execute(query)
            workers = result.scalars().all()
            # print(f"{workers=}")

    @staticmethod
    def update_worker(worker_id: int = 2, new_username: str = "Misha"):
        with session_factory() as session:
            worker_michael = session.get(WorkersOrm, worker_id)
            worker_michael.username = new_username
            # refresh нужен, если мы хотим заново подгрузить данные модели из базы.
            # Подходит, если мы давно получили модель и в это время
            # данные в базе данныхмогли быть изменены
            session.refresh(worker_michael)
            session.commit()

    @staticmethod
    def insert_resumes():
        with session_factory() as session:
            resume_jack_1 = ResumesOrm(
                title="Python Junior Developer", compensation=50000, workload=Workload.fulltime, worker_id=1)
            resume_jack_2 = ResumesOrm(
                title="Python Разработчик", compensation=150000, workload=Workload.fulltime, worker_id=1)
            resume_michael_1 = ResumesOrm(
                title="Python Data Engineer", compensation=250000, workload=Workload.parttime, worker_id=2)
            resume_michael_2 = ResumesOrm(
                title="Data Scientist", compensation=300000, workload=Workload.fulltime, worker_id=2)
            session.add_all([resume_jack_1, resume_jack_2, 
                             resume_michael_1, resume_michael_2])
            session.commit()

    @staticmethod
    def select_resumes_avg_compensation(like_language: str = "Python"):
        """
        select workload, avg(compensation)::int as avg_compensation
        from resumes
        where title like '%Python%' and compensation > 40000
        group by workload
        having avg(compensation) > 70000
        """
        with session_factory() as session:
            query = (
                select(
                    ResumesOrm.workload,
                    # 1 вариант использования cast
                    # cast(func.avg(ResumesOrm.compensation), Integer).label("avg_compensation"),
                    # 2 вариант использования cast (предпочтительный способ)
                    func.avg(ResumesOrm.compensation).cast(Integer).label("avg_compensation"),
                )
                .select_from(ResumesOrm)
                .filter(and_(
                    ResumesOrm.title.contains(like_language),
                    ResumesOrm.compensation > 40000,
                ))
                .group_by(ResumesOrm.workload)
                .having(func.avg(ResumesOrm.compensation) > 70000)
            )
            print(query.compile(compile_kwargs={"literal_binds": True}))
            res = session.execute(query)
            result = res.all()
            print(result[0].avg_compensation)

    @staticmethod
    def insert_additional_resumes():
        with session_factory() as session:
            workers = [
                {"username": "Artem"},  # id 3
                {"username": "Roman"},  # id 4
                {"username": "Petr"},   # id 5
            ]
            resumes = [
                {"title": "Python программист", "compensation": 60000, "workload": "fulltime", "worker_id": 3},
                {"title": "Machine Learning Engineer", "compensation": 70000, "workload": "parttime", "worker_id": 3},
                {"title": "Python Data Scientist", "compensation": 80000, "workload": "parttime", "worker_id": 4},
                {"title": "Python Analyst", "compensation": 90000, "workload": "fulltime", "worker_id": 4},
                {"title": "Python Junior Developer", "compensation": 100000, "workload": "fulltime", "worker_id": 5},
            ]
            insert_workers = insert(WorkersOrm).values(workers)
            insert_resumes = insert(ResumesOrm).values(resumes)
            session.execute(insert_workers)
            session.execute(insert_resumes)
            session.commit()

    @staticmethod
    def join_cte_subquery_window_func():
        """
        WITH helper2 AS (
            SELECT *, compensation-avg_workload_compensation AS compensation_diff
            FROM 
            (SELECT
                w.id,
                w.username,
                r.compensation,
                r.workload,
                avg(r.compensation) OVER (PARTITION BY workload)::int AS avg_workload_compensation
            FROM resumes r
            JOIN workers w ON r.worker_id = w.id) helper1
        )
        SELECT * FROM helper2
        ORDER BY compensation_diff DESC;
        """
        with session_factory() as session:
            r = aliased(ResumesOrm)
            w = aliased(WorkersOrm)
            subq = (
                select(
                    r,
                    w,
                    func.avg(r.compensation).over(partition_by=r.workload).cast(Integer).label("avg_workload_compensation"),
                )
                # .select_from(r)
                .join(r, r.worker_id == w.id).subquery("helper1")
            )
            cte = (
                select(
                    subq.c.worker_id,
                    subq.c.username,
                    subq.c.compensation,
                    subq.c.workload,
                    subq.c.avg_workload_compensation,
                    (subq.c.compensation - subq.c.avg_workload_compensation).label("compensation_diff"),
                )
                .cte("helper2")
            )
            query = (
                select(cte)
                .order_by(cte.c.compensation_diff.desc())
            )

            res = session.execute(query)
            result = res.all()
            # print(f"{len(result)=}. {result=}")

    @staticmethod
    def select_workers_with_lazy_relationship():
        with session_factory() as session:
            query = (
                select(WorkersOrm)
            )
            
            res = session.execute(query)
            result = res.scalars().all()

            worker_1_resumes = result[0].resumes
            print(worker_1_resumes)
            
            worker_2_resumes = result[1].resumes
            print(worker_2_resumes)

    @staticmethod
    def select_workers_with_joined_relationship():
        with session_factory() as session:
            query = (
                select(WorkersOrm)
                .options(joinedload(WorkersOrm.resumes))
            )
            
            res = session.execute(query)
            result = res.unique().scalars().all()

            worker_1_resumes = result[0].resumes
            print(worker_1_resumes)
            
            worker_2_resumes = result[1].resumes
            print(worker_2_resumes)

    @staticmethod
    def select_workers_with_selectin_relationship():
        with session_factory() as session:
            query = (
                select(WorkersOrm)
                .options(selectinload(WorkersOrm.resumes))
            )
            
            res = session.execute(query)
            result = res.scalars().all()

            worker_1_resumes = result[0].resumes
            # print(worker_1_resumes)
            
            worker_2_resumes = result[1].resumes
            # print(worker_2_resumes)

    @staticmethod
    def select_workers_with_condition_relationship():
        with session_factory() as session:
            query = (
                select(WorkersOrm)
                .options(selectinload(WorkersOrm.resumes_parttime))
            )

            res = session.execute(query)
            result = res.scalars().all()
            print(result)

    @staticmethod
    def select_workers_with_condition_relationship_contains_eager():
        with session_factory() as session:
            query = (
                select(WorkersOrm)
                .join(WorkersOrm.resumes)
                .options(contains_eager(WorkersOrm.resumes))
                .filter(ResumesOrm.workload == 'parttime')
            )

            res = session.execute(query)
            result = res.unique().scalars().all()
            print(result)

    @staticmethod
    def select_workers_with_relationship_contains_eager_with_limit():
        # Горячо рекомендую ознакомиться: https://stackoverflow.com/a/72298903/22259413 
        with session_factory() as session:
            subq = (
                select(ResumesOrm.id.label("parttime_resume_id"))
                .filter(ResumesOrm.worker_id == WorkersOrm.id)
                .order_by(WorkersOrm.id.desc())
                .limit(1)
                .scalar_subquery()
                .correlate(WorkersOrm)
            )

            query = (
                select(WorkersOrm)
                .join(ResumesOrm, ResumesOrm.id.in_(subq))
                .options(contains_eager(WorkersOrm.resumes))
            )

            res = session.execute(query)
            result = res.unique().scalars().all()
            print(result)

    @staticmethod
    def convert_workers_to_dto():
        with session_factory() as session:
            query = (
                select(WorkersOrm)
                .options(selectinload(WorkersOrm.resumes))
                .limit(2)
            )

            res = session.execute(query)
            result_orm = res.scalars().all()
            print(f"{result_orm=}")
            result_dto = [WorkersRelDTO.model_validate(row, from_attributes=True) for row in result_orm]
            print(f"{result_dto=}")
            return result_dto
        
    @staticmethod
    def add_vacancies_and_replies():
        with session_factory() as session:
            new_vacancy = VacanciesOrm(title="Python разработчик", compensation=100000)
            resume_1 = session.get(ResumesOrm, 1)
            resume_2 = session.get(ResumesOrm, 2)
            resume_1.vacancies_replied.append(new_vacancy)
            resume_2.vacancies_replied.append(new_vacancy)
            session.commit()

    @staticmethod
    def select_resumes_with_all_relationships():
        with session_factory() as session:
            query = (
                select(ResumesOrm)
                .options(joinedload(ResumesOrm.worker))
                .options(selectinload(ResumesOrm.vacancies_replied).load_only(VacanciesOrm.title))
            )

            res = session.execute(query)
            result_orm = res.unique().scalars().all()
            print(f"{result_orm=}")
            # Обратите внимание, что созданная в видео модель содержала лишний столбец compensation
            # И так как он есть в схеме ResumesRelVacanciesRepliedDTO, столбец compensation был вызван
            # Алхимией через ленивую загрузку. В асинхронном варианте это приводило к краху программы
            result_dto = [ResumesRelVacanciesRepliedWithoutVacancyCompensationDTO.model_validate(row, from_attributes=True) for row in result_orm]
            print(f"{result_dto=}")
            return result_dto


class AsyncORM:
    # Асинхронный вариант, не показанный в видео
    @staticmethod
    async def create_tables():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    @staticmethod
    async def insert_workers():
        async with async_session_factory() as session:
            worker_jack = WorkersOrm(username="Jack")
            worker_michael = WorkersOrm(username="Michael")
            session.add_all([worker_jack, worker_michael])
            # flush взаимодействует с БД, поэтому пишем await
            await session.flush()
            await session.commit()

    @staticmethod
    async def select_workers():
        async with async_session_factory() as session:
            query = select(WorkersOrm)
            result = await session.execute(query)
            workers = result.scalars().all()
            print(f"{workers=}")

    @staticmethod
    async def update_worker(worker_id: int = 2, new_username: str = "Misha"):
        async with async_session_factory() as session:
            worker_michael = await session.get(WorkersOrm, worker_id)
            worker_michael.username = new_username
            await session.refresh(worker_michael)
            await session.commit()

    @staticmethod
    async def insert_resumes():
        async with async_session_factory() as session:
            resume_jack_1 = ResumesOrm(
                title="Python Junior Developer", compensation=50000, workload=Workload.fulltime, worker_id=1)
            resume_jack_2 = ResumesOrm(
                title="Python Разработчик", compensation=150000, workload=Workload.fulltime, worker_id=1)
            resume_michael_1 = ResumesOrm(
                title="Python Data Engineer", compensation=250000, workload=Workload.parttime, worker_id=2)
            resume_michael_2 = ResumesOrm(
                title="Data Scientist", compensation=300000, workload=Workload.fulltime, worker_id=2)
            session.add_all([resume_jack_1, resume_jack_2, 
                             resume_michael_1, resume_michael_2])
            await session.commit()

    @staticmethod
    async def select_resumes_avg_compensation(like_language: str = "Python"):
        """
        select workload, avg(compensation)::int as avg_compensation
        from resumes
        where title like '%Python%' and compensation > 40000
        group by workload
        having avg(compensation) > 70000
        """
        async with async_session_factory() as session:
            query = (
                select(
                    ResumesOrm.workload,
                    # 1 вариант использования cast
                    # cast(func.avg(ResumesOrm.compensation), Integer).label("avg_compensation"),
                    # 2 вариант использования cast (предпочтительный способ)
                    func.avg(ResumesOrm.compensation).cast(Integer).label("avg_compensation"),
                )
                .select_from(ResumesOrm)
                .filter(and_(
                    ResumesOrm.title.contains(like_language),
                    ResumesOrm.compensation > 40000,
                ))
                .group_by(ResumesOrm.workload)
                .having(func.avg(ResumesOrm.compensation) > 70000)
            )
            print(query.compile(compile_kwargs={"literal_binds": True}))
            res = await session.execute(query)
            result = res.all()
            print(result[0].avg_compensation)

    @staticmethod
    async def insert_additional_resumes():
        async with async_session_factory() as session:
            workers = [
                {"username": "Artem"},  # id 3
                {"username": "Roman"},  # id 4
                {"username": "Petr"},   # id 5
            ]
            resumes = [
                {"title": "Python программист", "compensation": 60000, "workload": "fulltime", "worker_id": 3},
                {"title": "Machine Learning Engineer", "compensation": 70000, "workload": "parttime", "worker_id": 3},
                {"title": "Python Data Scientist", "compensation": 80000, "workload": "parttime", "worker_id": 4},
                {"title": "Python Analyst", "compensation": 90000, "workload": "fulltime", "worker_id": 4},
                {"title": "Python Junior Developer", "compensation": 100000, "workload": "fulltime", "worker_id": 5},
            ]
            insert_workers = insert(WorkersOrm).values(workers)
            insert_resumes = insert(ResumesOrm).values(resumes)
            await session.execute(insert_workers)
            await session.execute(insert_resumes)
            await session.commit()

    @staticmethod
    async def join_cte_subquery_window_func():
        """
        WITH helper2 AS (
            SELECT *, compensation-avg_workload_compensation AS compensation_diff
            FROM 
            (SELECT
                w.id,
                w.username,
                r.compensation,
                r.workload,
                avg(r.compensation) OVER (PARTITION BY workload)::int AS avg_workload_compensation
            FROM resumes r
            JOIN workers w ON r.worker_id = w.id) helper1
        )
        SELECT * FROM helper2
        ORDER BY compensation_diff DESC;
        """
        async with async_session_factory() as session:
            r = aliased(ResumesOrm)
            w = aliased(WorkersOrm)
            subq = (
                select(
                    r,
                    w,
                    func.avg(r.compensation).over(partition_by=r.workload).cast(Integer).label("avg_workload_compensation"),
                )
                # .select_from(r)
                .join(r, r.worker_id == w.id).subquery("helper1")
            )
            cte = (
                select(
                    subq.c.worker_id,
                    subq.c.username,
                    subq.c.compensation,
                    subq.c.workload,
                    subq.c.avg_workload_compensation,
                    (subq.c.compensation - subq.c.avg_workload_compensation).label("compensation_diff"),
                )
                .cte("helper2")
            )
            query = (
                select(cte)
                .order_by(cte.c.compensation_diff.desc())
            )

            res = await session.execute(query)
            result = res.all()
            print(f"{len(result)=}. {result=}")

    @staticmethod
    async def select_workers_with_lazy_relationship():
        async with async_session_factory() as session:
            query = (
                select(WorkersOrm)
            )
            
            res = await session.execute(query)
            result = res.scalars().all()

            # worker_1_resumes = result[0].resumes  # -> Приведет к ошибке
            # Нельзя использовать ленивую подгрузку в асинхронном варианте!

            # Ошибка: sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. 
            # Was IO attempted in an unexpected place? (Background on this error at: https://sqlalche.me/e/20/xd2s)
            

    @staticmethod
    async def select_workers_with_joined_relationship():
        async with async_session_factory() as session:
            query = (
                select(WorkersOrm)
                .options(joinedload(WorkersOrm.resumes))
            )
            
            res = await session.execute(query)
            result = res.unique().scalars().all()

            worker_1_resumes = result[0].resumes
            # print(worker_1_resumes)
            
            worker_2_resumes = result[1].resumes
            # print(worker_2_resumes)

    @staticmethod
    async def select_workers_with_selectin_relationship():
        async with async_session_factory() as session:
            query = (
                select(WorkersOrm)
                .options(selectinload(WorkersOrm.resumes))
            )
            
            res = await session.execute(query)
            result = res.scalars().all()

            worker_1_resumes = result[0].resumes
            # print(worker_1_resumes)
            
            worker_2_resumes = result[1].resumes
            # print(worker_2_resumes)

    @staticmethod
    async def select_workers_with_condition_relationship():
        async with async_session_factory() as session:
            query = (
                select(WorkersOrm)
                .options(selectinload(WorkersOrm.resumes_parttime))
            )

            res = await session.execute(query)
            result = res.scalars().all()
            print(result)

    @staticmethod
    async def select_workers_with_condition_relationship_contains_eager():
        async with async_session_factory() as session:
            query = (
                select(WorkersOrm)
                .join(WorkersOrm.resumes)
                .options(contains_eager(WorkersOrm.resumes))
                .filter(ResumesOrm.workload == 'parttime')
            )

            res = await session.execute(query)
            result = res.unique().scalars().all()
            print(result)

    @staticmethod
    async def select_workers_with_relationship_contains_eager_with_limit():
        # Горячо рекомендую ознакомиться: https://stackoverflow.com/a/72298903/22259413 
        async with async_session_factory() as session:
            subq = (
                select(ResumesOrm.id.label("parttime_resume_id"))
                .filter(ResumesOrm.worker_id == WorkersOrm.id)
                .order_by(WorkersOrm.id.desc())
                .limit(1)
                .scalar_subquery()
                .correlate(WorkersOrm)
            )

            query = (
                select(WorkersOrm)
                .join(ResumesOrm, ResumesOrm.id.in_(subq))
                .options(contains_eager(WorkersOrm.resumes))
            )

            res = await session.execute(query)
            result = res.unique().scalars().all()
            print(result)

    @staticmethod
    async def convert_workers_to_dto():
        async with async_session_factory() as session:
            query = (
                select(WorkersOrm)
                .options(selectinload(WorkersOrm.resumes))
                .limit(2)
            )

            res = await session.execute(query)
            result_orm = res.scalars().all()
            print(f"{result_orm=}")
            result_dto = [WorkersRelDTO.model_validate(row, from_attributes=True) for row in result_orm]
            print(f"{result_dto=}")
            return result_dto
        
    @staticmethod
    async def add_vacancies_and_replies():
        async with async_session_factory() as session:
            new_vacancy = VacanciesOrm(title="Python разработчик", compensation=100000)
            get_resume_1 = select(ResumesOrm).options(selectinload(ResumesOrm.vacancies_replied)).filter_by(id=1)
            get_resume_2 = select(ResumesOrm).options(selectinload(ResumesOrm.vacancies_replied)).filter_by(id=2)
            resume_1 = (await session.execute(get_resume_1)).scalar_one()
            resume_2 = (await session.execute(get_resume_2)).scalar_one()
            resume_1.vacancies_replied.append(new_vacancy)
            resume_2.vacancies_replied.append(new_vacancy)
            await session.commit()

    @staticmethod
    async def select_resumes_with_all_relationships():
        async with async_session_factory() as session:
            query = (
                select(ResumesOrm)
                .options(joinedload(ResumesOrm.worker))
                .options(selectinload(ResumesOrm.vacancies_replied).load_only(VacanciesOrm.title))
            )

            res = await session.execute(query)
            result_orm = res.unique().scalars().all()
            print(f"{result_orm=}")
            # Обратите внимание, что созданная в видео модель содержала лишний столбец compensation
            # И так как он есть в схеме ResumesRelVacanciesRepliedDTO, столбец compensation был вызван
            # Алхимией через ленивую загрузку. В асинхронном варианте это приводило к краху программы
            result_dto = [ResumesRelVacanciesRepliedWithoutVacancyCompensationDTO.model_validate(row, from_attributes=True) for row in result_orm]
            print(f"{result_dto=}")
            return result_dto
