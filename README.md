Find your pipenv venv path first:
```
pipenv --venv
# e.g. /home/sourabh/.local/share/virtualenvs/examtopics.app-xxxxxxxx
```

```
[Unit]
Description=ExamTopics FastAPI App
After=network.target

[Service]
User=sourabh
WorkingDirectory=/home/sourabh/examtopics.app
ExecStart=/home/sourabh/.local/share/virtualenvs/examtopics.app-Omml76t6/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
EnvironmentFile=/home/sourabh/examtopics.app/.env

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl daemon-reload
sudo systemctl enable examtopics
sudo systemctl start examtopics
sudo systemctl status examtopics
```

```
journalctl -u examtopics -f   #live logs
journalctl -u examtopics --since today  # today's logs
```