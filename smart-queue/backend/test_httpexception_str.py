from fastapi import HTTPException

e = HTTPException(status_code=500, detail="Failed to generate unique token due to concurrency")
print("str(e) is:", repr(str(e)))
