# Trade Backend

FastAPI backend for the foreign trade AI workbench.

## Local development

```bash
pip install -r requirements.txt
alembic upgrade head
python start.py
```

## Render

Use `render.yaml` from the repository root, or configure manually:

```txt
Build Command: pip install -r requirements.txt
Pre-Deploy Command: alembic upgrade head
Start Command: python start.py
```
