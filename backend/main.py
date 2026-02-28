from fastapi import FastAPI

# Initialize the FastAPI app
app = FastAPI(
    title="My FastAPI Backend",
    description="A simple backend to get started",
    version="1.0.0"
)

# Define a root endpoint
@app.get("/")
def read_root():
    return {"message": "Hello World! Welcome to FastAPI."}

# Define an endpoint with a path parameter
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "query_parameter": q}