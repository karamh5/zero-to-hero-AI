from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4, UUID #unique id for each task

app = FastAPI() #creat instance of the FastAPI class

class Task(BaseModel):
    id: Optional[UUID] = None #optional because don't have to 
    title: str #must have a title to create a task
    description: Optional[str] = None
    completed: bool = False

tasks = [] #usually connected to a database but here we are using a list to store the tasks

@app.post("/tasks", response_model=Task) #define a route
def create_task(task: Task): #accepts a Task object and returns a Task object
    task.id = uuid4()
    tasks.append(task)
    return task

@app.get("/tasks", response_model=List[Task]) #define a route
def read_tasks():
    return tasks #returns the list of tasks

if __name__ == "__main__": #run the app
    import uvicorn #import uvicorn to run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)