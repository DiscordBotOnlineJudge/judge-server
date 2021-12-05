from concurrent import futures
import time
import os
import grpc
import judge_pb2
import judge_pb2_grpc
import submission
import yaml
import sys
from google.cloud import storage
from pymongo import MongoClient

judgeSettings = yaml.safe_load(open("JudgeSetup.yaml", "r"))
judgeNum = judgeSettings['JudgeNum']
portNum = judgeSettings['port']

lang_dict = yaml.safe_load(open("lang.yaml", "r"))

class Listener(judge_pb2_grpc.JudgeServiceServicer):
    def __init__(self):
        pass

    def __str__(self):
        return self.__class__.__name__

    def judge(self, request, context):
        print("Received judge request")
        try:
            score = submission.submit(storage_client, settings, request.username, request.source, request.lang, request.problem, judgeNum, request.attachment, lang_dict[request.lang])
        except:
            print("Fatal error:\n" + sys.exc_info()[0])
        return judge_pb2.SubmissionResult(finalScore = score[0], error = open("errors.txt").read(1000), finalOutput = score[1])


def serve():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-service-key.json'
    stc = storage.Client()

    # Google Cloud Storage Client
    global storage_client
    storage_client = stc.get_bucket('discord-bot-oj-file-storage')

    # Pymongo Client
    pswd = open("PASSWORD", "r").read().strip()
    cluster = MongoClient("mongodb+srv://onlineuser:$" + pswd + "@discord-bot-online-judg.7gm4i.mongodb.net/database?retryWrites=true&w=majority")
    db = cluster['database']
    global settings
    settings = db['settings']

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    judge_pb2_grpc.add_JudgeServiceServicer_to_server(Listener(), server)
    server.add_insecure_port("[::]:" + str(portNum))
    server.start()

    print("Server running on host port " + str(portNum))

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        server.stop(0)

if __name__ == "__main__":
    serve()