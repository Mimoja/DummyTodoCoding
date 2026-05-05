import argparse
import json
import datetime
import os
from print_color import print

TODOS_PATH = os.getenv("TODOS_PATH", ".")
TODOS_FILE_NAME = os.getenv("TODOS_FILE", "todos.json")
TODOS_FILE = os.path.join(TODOS_PATH, TODOS_FILE_NAME)

todos = []


def getUTCTimestamp() -> float:
    dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.timestamp()


class Todo:

    id: int
    description: str
    context: str | None
    completed_on: float | None

    def __init__(
        self, id: int, description: str, context: str | None, completed_on: float | None
    ):
        self.id = id
        self.description = description
        self.context = context if context is not None and context != "" else None
        self.completed_on = completed_on

    def toJSON(self):
        return {
            "id": self.id,
            "description": self.description,
            "context": self.context,
            "completed_on": self.completed_on,
        }


def writeTodos():
    tmpfile = os.path.join(TODOS_PATH, "_tmp.json")

    with open(tmpfile, mode="w+") as f:
        f.write(json.dumps([todo.__dict__ for todo in todos], indent=2))

    os.replace(tmpfile, TODOS_FILE)


def readTodos():
    global todos

    if not os.path.exists(TODOS_FILE):
        todos = []
        writeTodos()
        return

    try:
        with open(TODOS_FILE) as f:
            todos = [Todo(**todo) for todo in json.load(f)]
    except Exception as e:
        print(
            f"I am sad, everything is sad. Repair {TODOS_FILE} and try again! Error:",
            e,
            color="red",
        )
        exit()


def list_todos():
    if not todos:
        print("No todos", color="white")

    for todo in todos:
        completed = ""
        if todo.completed_on:
            try:
                utc_dt = datetime.datetime.fromtimestamp(
                    todo.completed_on, datetime.UTC
                )
                timestring = utc_dt.astimezone().strftime("%d.%m.%Y %I:%M %p")
                completed = f" Completed on: {timestring}  "
            except Exception:
                pass

        print(
            completed,
            todo.description,
            tag=str(todo.id),
            tag_color="green" if todo.completed_on is not None else "yellow",
            color="white",
            end="",
        )

        if todo.context:
            print("  ", todo.context, color="magenta")


def add_todo(desc: str, context: str | None):
    global todos
    next_id = max([todo.id for todo in todos] or [0]) + 1

    todos.append(Todo(next_id, desc, context, None))
    writeTodos()


def mark_done(id: int):
    global todos
    todo_ind = [indx for indx, todo in enumerate(todos) if todo.id == id]
    if not todo_ind:
        print("No TODO found with this ID", color="red")
        return

    todos[todo_ind[0]].completed_on = getUTCTimestamp()

    writeTodos()


def del_todo(id: int):
    todo_ind = [indx for indx, todo in enumerate(todos) if todo.id == id]
    if not todo_ind:
        print("No TODO found with this ID", color="red")
        return
    del todos[todo_ind[0]]
    writeTodos()


def main():

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command")

    # List parser without args
    subparser.add_parser("list")

    add_parser = subparser.add_parser("add")
    add_parser.add_argument(
        "description", help="The short Description of the todo", type=str
    )
    add_parser.add_argument(
        "context",
        help="Optional extra context for the todo",
        default=None,
        type=str,
        nargs="?",
    )

    del_parser = subparser.add_parser("delete")
    del_parser.add_argument(
        "ID", help="ID of the TODO item (use the list argument)", type=int
    )

    compl_parser = subparser.add_parser("done")
    compl_parser.add_argument(
        "ID", help="ID of the TODO item (use the list argument)", type=int
    )

    args = parser.parse_args()

    readTodos()

    match args.command:
        case "list":
            list_todos()
        case "add":
            add_todo(args.description, args.context)
        case "delete":
            del_todo(args.ID)
        case "done":
            mark_done(args.ID)
        case _:
            parser.print_help()
            exit()


if __name__ == "__main__":
    main()
