import io
import sys
from contextlib import redirect_stdout
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.training import Lesson

router = APIRouter(tags=["Code Execution"])

class CodeExecutionRequest(BaseModel):
    code: str
    lesson_id: str

def execute_user_code(code: str):
    output_buffer = io.StringIO()
    global_scope = {}
    try:
        with redirect_stdout(output_buffer):
            exec(code, global_scope)
        output = output_buffer.getvalue()
        return {"output": output, "error": None, "scope": global_scope}
    except Exception as e:
        return {"output": None, "error": str(e), "scope": {}}

@router.post("/execute")
def execute_code(request: CodeExecutionRequest, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == request.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    result = execute_user_code(request.code)
    if result["error"]:
        return {"success": False, "message": f"Execution Error: {result['error']}", "output": result["error"]}

    output = result["output"]
    criteria = lesson.validation_criteria
    if not criteria:
        return {"success": True, "message": "Code executed successfully.", "output": output}

    validation_type = criteria.get("type", "exact_match")
    expected = criteria.get("expected")
    
    success = False
    message = "The code ran, but the output isn't quite right. Keep trying!"

    if validation_type == "exact_match":
        if output.strip() == expected.strip():
            success = True
            message = "Correct! The output is an exact match. Well done!"
    elif validation_type == "contains":
        if expected in output:
            success = True
            message = f"Great! The output contains the required text: '{expected}'."
    elif validation_type == "function_call":
        func_name = criteria.get("function_name")
        args = criteria.get("args", [])
        user_func = result["scope"].get(func_name)

        if not user_func:
            message = f"Validation failed: Function '{func_name}' not found in your code."
        elif not callable(user_func):
            message = f"Validation failed: '{func_name}' is not a function."
        else:
            try:
                actual_result = user_func(*args)
                if actual_result == expected:
                    success = True
                    message = f"Excellent! Calling `{func_name}({', '.join(map(str, args))})` produced the correct result: {expected}."
                else:
                    message = f"Close! Calling `{func_name}({', '.join(map(str, args))})` returned `{actual_result}`, but we expected `{expected}`."
            except Exception as e:
                message = f"An error occurred while calling your function: {e}"

    return {"success": success, "message": message, "output": output}

