## Prepare
Use `pip3 install -r requirements.txt` to install required modules

## Start
Use `nohup python3 main.py > /dev/null &` to run in the background

## Stop
Use `kill $(cat .pid)` to kill the process in the background with pid

Use `pkill -9 -f run_bot.py` to kill all run_bot.py processes if you lost the pid
