import asyncio
import os
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from queries.core import AsyncCore, SyncCore
from queries.orm import AsyncORM, SyncORM


async def main():
    # ========== SYNC ==========
    # CORE
    if "--core" in sys.argv and "--sync" in sys.argv:
        SyncCore.create_tables()
        SyncCore.insert_workers()
        SyncCore.select_workers()
        SyncCore.update_worker()
        SyncCore.insert_resumes()
        SyncCore.select_resumes_avg_compensation()
        SyncCore.insert_additional_resumes()
        SyncCore.join_cte_subquery_window_func()

    # ORM
    elif "--orm" in sys.argv and "--sync" in sys.argv:
        SyncORM.create_tables()
        SyncORM.insert_workers()
        SyncORM.select_workers()
        SyncORM.update_worker()
        SyncORM.insert_resumes()
        SyncORM.select_resumes_avg_compensation()
        SyncORM.insert_additional_resumes()
        SyncORM.join_cte_subquery_window_func()
        SyncORM.select_workers_with_lazy_relationship()
        SyncORM.select_workers_with_joined_relationship()
        SyncORM.select_workers_with_selectin_relationship()
        SyncORM.select_workers_with_condition_relationship()
        SyncORM.select_workers_with_condition_relationship_contains_eager()
        SyncORM.select_workers_with_relationship_contains_eager_with_limit()
        SyncORM.convert_workers_to_dto()
        SyncORM.add_vacancies_and_replies()
        SyncORM.select_resumes_with_all_relationships()

    # ========== ASYNC ==========
    # CORE
    elif "--core" in sys.argv and "--async" in sys.argv:
        await AsyncCore.create_tables()
        await AsyncCore.insert_workers()
        await AsyncCore.select_workers()
        await AsyncCore.update_worker()
        await AsyncCore.insert_resumes()
        await AsyncCore.select_resumes_avg_compensation()
        await AsyncCore.insert_additional_resumes()
        await AsyncCore.join_cte_subquery_window_func()

    # ORM
    elif "--orm" in sys.argv and "--async" in sys.argv:
        await AsyncORM.create_tables()
        await AsyncORM.insert_workers()
        await AsyncORM.select_workers()
        await AsyncORM.update_worker()
        await AsyncORM.insert_resumes()
        await AsyncORM.select_resumes_avg_compensation()
        await AsyncORM.insert_additional_resumes()
        await AsyncORM.join_cte_subquery_window_func()
        await AsyncORM.select_workers_with_lazy_relationship()
        await AsyncORM.select_workers_with_joined_relationship()
        await AsyncORM.select_workers_with_selectin_relationship()
        await AsyncORM.select_workers_with_condition_relationship()
        await AsyncORM.select_workers_with_condition_relationship_contains_eager()
        await AsyncORM.select_workers_with_relationship_contains_eager_with_limit()
        await AsyncORM.convert_workers_to_dto()
        await AsyncORM.add_vacancies_and_replies()
        await AsyncORM.select_resumes_with_all_relationships()


def create_fastapi_app():
    app = FastAPI(title="FastAPI")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
    )
        
    @app.get("/workers", tags=["Кандидат"])
    async def get_workers():
        workers = SyncORM.convert_workers_to_dto()
        return workers
        
    @app.get("/resumes", tags=["Резюме"])
    async def get_resumes():
        resumes = await AsyncORM.select_resumes_with_all_relationships()
        return resumes
    
    return app
    

app = create_fastapi_app()


if __name__ == "__main__":
    asyncio.run(main())
    if "--webserver" in sys.argv:
        uvicorn.run(
            app="src.main:app",
            reload=True,
        )
