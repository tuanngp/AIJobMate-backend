@echo off
call venv\Scripts\activate.bat
@REM alembic revision --autogenerate -m "setup migration"
@REM alembic upgrade head
python run.py
