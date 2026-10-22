# Dailies


Made by:
Alexander Tuero
Bernardo Lopez
Cristian Ravelo

## Developer Set-Up
To set up Django do
'''
git clone <repo-url>
cd <repo-name>
python3 -m venv venv
source venv/bin/activate
cd backend
pip install -r requirements.txt
cp .env.example .env     # then fill in .env with real values
python manage.py migrate
python manage.py runserver
...