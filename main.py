import argparse
import json
import datetime
import os
from print_color import print

TODOS_PATH = os.getenv("TODOS_PATH", ".")
TODOS_FILE_NAME = os.getenv("TODOS_FILE", "todos.json")
TODOS_FILE = os.path.join(TODOS_PATH, TODOS_FILE_NAME)

todos = []
journal = []


def getUTCTimestamp() -> float:
    dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.timestamp()


class Todo:

    id: int
    description: str
    context: str | None
    completed_on: float | None
    priority: str | None

    def __init__(
        self,
        id: int,
        description: str,
        context: str | None = None,
        completed_on: float | None = None,
        priority: str | None = "middle",
    ):
        self.id = id
        self.description = description
        self.context = context if context is not None and context != "" else None
        self.completed_on = completed_on
        self.priority = priority or "middle"

    def toJSON(self):
        return self.__dict__


class JournalEntry:
    action: str
    todo_id: int
    pre_todo: Todo | None

    def __init__(self, action: str, todo_id: int, pre_todo: Todo | None | dict = None):
        self.action = action
        self.todo_id = todo_id
        if isinstance(pre_todo, dict):
            pre_todo = Todo(**pre_todo)
        self.pre_todo = pre_todo

    def toJSON(self):
        return {
            "action": self.action,
            "todo_id": self.todo_id,
            "pre_todo": self.pre_todo.toJSON() if self.pre_todo else None,
        }


def writeTodos():
    tmpfile = os.path.join(TODOS_PATH, "_tmp.json")

    journal_to_safe = journal[-10:]
    data = {
        "journal": [j.toJSON() for j in journal_to_safe],
        "todos": [todo.toJSON() for todo in todos],
    }

    with open(tmpfile, mode="w+") as f:
        f.write(json.dumps(data, indent=2))

    os.replace(tmpfile, TODOS_FILE)


def readTodos():
    global todos
    global journal

    if not os.path.exists(TODOS_FILE):
        todos = []
        journal = []
        writeTodos()
        return

    try:
        with open(TODOS_FILE) as f:
            json_data = json.load(f)
            if isinstance(json_data, list):
                journal = []
                todos = [Todo(**todo) for todo in json_data]
                writeTodos()
            else:
                journal = [JournalEntry(**j) for j in json_data.get("journal", [])]
                todos = [Todo(**todo) for todo in json_data.get("todos", [])]
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
            f"[{todo.id}]",
            completed,
            todo.description,
            tag=todo.priority or "default",
            tag_color=(
                "green"
                if todo.completed_on is not None
                else "red" if todo.priority == "high" else "yellow"
            ),
            color="white",
            end="",
        )

        print("  ", todo.context or "", color="magenta")


def add_todo(desc: str, context: str | None):
    global todos
    if not context:
        descriptions = [d.strip() for d in desc.split(",")]
    else:
        descriptions = [desc]

    for description in descriptions:
        next_id = max([todo.id for todo in todos] or [0]) + 1
        todos.append(Todo(next_id, description, context, None, "middle"))

        journal.append(JournalEntry("add", next_id, None))
    writeTodos()


def mark_done(id: int):
    global todos
    todo_ind = [indx for indx, todo in enumerate(todos) if todo.id == id]
    if not todo_ind:
        print("No TODO found with this ID", color="red")
        return

    journal.append(JournalEntry("done", todos[todo_ind[0]].id, todos[todo_ind[0]]))
    todos[todo_ind[0]].completed_on = getUTCTimestamp()

    writeTodos()


def del_todo(id: int):
    todo_ind = [indx for indx, todo in enumerate(todos) if todo.id == id]
    if not todo_ind:
        print("No TODO found with this ID", color="red")
        return
    journal.append(JournalEntry("delete", todos[todo_ind[0]].id, todos[todo_ind[0]]))
    del todos[todo_ind[0]]

    writeTodos()


def prio_todo(id: int, priority: str):
    global todos
    todo_ind = [indx for indx, todo in enumerate(todos) if todo.id == id]
    if not todo_ind:
        print("No TODO found with this ID", color="red")
        return

    journal.append(JournalEntry("prio", todos[todo_ind[0]].id, todos[todo_ind[0]]))
    todos[todo_ind[0]].priority = priority

    writeTodos()


def undo_action():
    global journal

    if not journal:
        print("No actions to undo", color="red")
        exit()

    last_action = journal[-1]
    print(
        f"Undoing {last_action.action} for todo no {last_action.todo_id}",
        color="magenta",
    )

    todo_ind = [
        indx for indx, todo in enumerate(todos) if todo.id == last_action.todo_id
    ]

    if last_action.action == "add":
        if not todo_ind:
            print("Invalid journal state, cannot roll back", color="red")
            return
        del todos[todo_ind[0]]
    elif last_action.action == "delete":
        if not last_action.pre_todo:
            print("Invalid journal state, cannot roll back", color="red")
            return
        todos.append(last_action.pre_todo)
    else:
        if not todo_ind or not last_action.pre_todo:
            print("Invalid journal state, cannot roll back", color="red")
            return

        todos[todo_ind[0]] = last_action.pre_todo
    journal.pop()
    writeTodos()


def main():

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command")

    # List parser without args
    subparser.add_parser("list")
    subparser.add_parser("undo")

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

    prio_parser = subparser.add_parser("prio")
    prio_parser.add_argument(
        "ID", help="ID of the TODO item (use the list argument)", type=int
    )
    prio_parser.add_argument(
        "Priority",
        help="ID of the TODO item (use the list argument)",
        type=str,
        choices=["low", "middle", "high"],
    )
    args = parser.parse_args()

    readTodos()

    match args.command:
        case "list":
            list_todos()
        case "undo":
            undo_action()
        case "add":
            add_todo(args.description, args.context)
        case "delete":
            del_todo(args.ID)
        case "prio":
            prio_todo(args.ID, args.Priority)
        case "done":
            mark_done(args.ID)
        case _:
            parser.print_help()
            exit()


if __name__ == "__main__":
    main()
