from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from config import templates
from fastapi.responses import RedirectResponse
from routers import user_routes, beneficiary_routes, admin_routes, volunteer_routes, admin_volunteer_routes
from database import execute_sql_commands, initate_database_tables, execute_sql_select_statement
# from contextlib import asynccontextmanager




# @asynccontextmanager
# async def app_lifespan(app: FastAPI):
#     try:
#         initate_database_tables() # Initalizing the database tables.
#         print("Life span starts")
#     except Exception as e:
#         print(f"Error occurs while initializing database tables : {e}")
#         raise 
#     yield # yield the control to the application.
            


app: FastAPI = FastAPI(
    title = "Sourashtra Engineers and Technologists Network",
    version = "0.1.0",
    # lifespan = app_lifespan
) 


app.mount("/static", StaticFiles(directory = "static"), name = "static")

app.include_router(user_routes.router)
app.include_router(beneficiary_routes.router)
app.include_router(admin_routes.router)
app.include_router(volunteer_routes.router)
app.include_router(admin_volunteer_routes.router)




@app.get('/test')
def test_path():
    return "Shivaya Namah"

@app.get("/")
def root_page(request: Request):
    return RedirectResponse(url="/index", status_code = status.HTTP_307_TEMPORARY_REDIRECT)
