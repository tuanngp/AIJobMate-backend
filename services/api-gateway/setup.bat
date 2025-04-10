@echo off
echo Installing dependencies...
python -m pip install -r requirements.txt

echo.
echo Setup completed successfully!
echo To run the API Gateway in development mode, use: python run.py --reload
echo The gateway will be available at http://localhost:8000