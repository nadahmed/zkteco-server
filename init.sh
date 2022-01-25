if [[ ! -e /code/test.db ]]; then
    echo "File does not exist in Bash"
    echo "Running database migrations..."
    alembic upgrade head
else
    echo "File found. Do something meaningful here"
fi

uvicorn main:app --host 0.0.0.0 --port 8000