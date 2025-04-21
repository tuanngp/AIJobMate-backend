@echo off
echo Installing dependencies...
python -m pip install -r requirements.txt

@echo off
call venv\Scripts\activate.bat
alembic revision --autogenerate -m "setup migration"
alembic upgrade head

echo.
echo Setup completed successfully!
echo To run the auth service in development mode, use: python run.py --reload
