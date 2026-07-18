from fastapi import APIRouter
import sys
import traceback

router = APIRouter()

# Global list to store last 5 exceptions
last_exceptions = []

def exception_handler(exc_type, exc_value, exc_traceback):
    global last_exceptions
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    last_exceptions.append(tb_str)
    if len(last_exceptions) > 5:
        last_exceptions.pop(0)
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = exception_handler

@router.get("/exceptions")
def get_exceptions():
    return {"exceptions": last_exceptions}
