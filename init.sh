#!/bin/bash

FILE=/code/test.db
if [ -f "$FILE" ]; then
    echo "File found. Do something meaningful here"
else
    echo "File does not exist in Bash"
    echo "Running database migrations..."
    alembic upgrade head   

fi
echo "Running server now"

uvicorn main:app --host 0.0.0.0 --port 8000

exit 0