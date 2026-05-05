# ReVoltz Backend

Backend API for the ReVoltz workshop, inventory, auth, and marketplace flows. Built with FastAPI + SQLite.

## Run locally

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in `backend/` if needed:

```env
ALLOWED_ORIGINS=http://localhost:5173
MODEL_API_URL=http://localhost:8001
DATABASE_URL=sqlite:///./revoltz.db
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

4. Start the backend API:

```bash
uvicorn app:app --reload --port 8000
```

5. Open:

```text
http://localhost:8000/docs
```

## Notes

- This backend expects the model API to be running separately on `http://localhost:8001`.
- Default local database is `backend/revoltz.db`.
