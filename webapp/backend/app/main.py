from fastapi import FastAPI
from mangum import Mangum
from .application import trips_api

app = FastAPI(title="Api Trips Uber")

app.include_router(trips_api)
handler = Mangum(app)


