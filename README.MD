Create .env file. Fill it with necessary variables

```
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
```

Start postgresql via docker compose (Starts on default 5432 port)

```
docker compose up -d
```

Create python enviroment and install requirements

```
python3 -m venv venv
source .venv/bin/activate
pip install -r requirements.txt
```

Apply migrations

```
flask db upgrade
```

Start the app


```
python3 app.py
```

The app will start on localhost on port 5000.
Access web-page in the browser via http://0.0.0.0:5000/.
