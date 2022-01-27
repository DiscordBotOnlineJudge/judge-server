# DBOJ Judge Grading Server
Submission grading server for the Discord Bot Online Judge backend.

## Setting up a judge
Clone this repository and enter the judge-server directory.
```bash
git clone https://github.com/DiscordBotOnlineJudge/judge-server.git
cd judge-server
```

Configure the judge number by creating a directory named `Judge` followed by the judge number you would like. For example,
```bash
mkdir Judge1
```

Change the values in `JudgeSetup.yaml` to the settings you would like:
```yaml
JudgeNum: [judge number]
port: [port to host the server on]
```

Run the language setup batch file:
```bash
bash langsetup.bash
```

## Running the judge-server listener
The judge uses gRPC to listen for submissions from the Discord bot interface.
Make sure you have `gRPC` installed on your machine.
```bash
python3 -m pip install --upgrade pip  # Update your pip installer
pip3 install grpcio
pip3 install grpcio-tools
```

To run the judge, call the judge_server.py listener
```bash
python3 judge_server.py
```

The server should respond with
```
Server running on host port [host number]
```
