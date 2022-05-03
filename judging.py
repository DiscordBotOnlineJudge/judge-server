# This file contains methods that the judge uses to determine
# a verdict for a submission test case

from multiprocessing.sharedctypes import Value
import time
import os
import subprocess
import math
import asyncio
import yaml
import sys
import traceback, requests

compTimeout = 15

def cleanChecker(fn, jn):
    f = open(fn, "r")
    src = f.read().replace("data.in", "Judge" + jn + "/data.in").replace("data.out", "Judge" + jn + "/data.out").replace("expected.out", "Judge" + jn + "/expected.out")
    f.flush()
    f.close()

    w = open(fn, "w")
    w.write(src)
    w.flush()
    w.close()

def cleanNullChars(output):
    res = ""
    for x in output:
        if ord(x) != 0:
            res += x
    return res

def checkEqual(problem, bat, case, judgeNum, storage_client):
    try:
        write_file(storage_client, problem, bat, case, "out", "Judge" + str(judgeNum) + "/expected.out")
    except:
        pass

    try:
        get_file(storage_client, "TestData/" + problem + "/checker.py", "Judge" + str(judgeNum) + "/checker.py")
        myOutput = open("Judge" + str(judgeNum) + "/verdict.out", "w") 

        cleanChecker("Judge" + str(judgeNum) + "/checker.py", str(judgeNum))

        check = subprocess.Popen("python3 Judge" + str(judgeNum) + "/checker.py Judge" + str(judgeNum) + "/data.in Judge" + str(judgeNum) + "/data.out", stdout=myOutput, shell=True)
        code = check.wait(3)

        if code != 0:
            return False

        myOutput.flush()
        myOutput.close()

        with open("Judge" + str(judgeNum) + "/verdict.out") as f:
            verdict = f.read().strip()
            return (verdict.endswith("CORRECT"), verdict)

    except:
        cor = open("Judge" + str(judgeNum) + "/expected.out", "r")
        giv = open("Judge" + str(judgeNum) + "/data.out", "r")

        expect = cor.read()
        mine = giv.read()

        idx = 0
        for line in expect.split("\n"):
            if not line: continue
            try:
                pos = mine.index(line, idx) 
                idx = pos + len(line)
            except ValueError:
                print("Test point failed:", line)
                return (False, open("Judge" + str(judgeNum) + "/data.out", "r").read(1000))

        giv.flush()
        giv.close()
        cor.flush()
        cor.close()

        return (True, open("Judge" + str(judgeNum) + "/data.out", "r").read(1000))

def get_file(storage_client, blobname, save):
    blob = storage_client.blob(blobname)
    blob.download_to_filename(save)

def write_file(storage_client, problem, bat, case, ext, save):
    blob = storage_client.blob("TestData/" + problem + "/data" + str(bat) + "." + str(case) + "." + ext)
    blob.download_to_filename(save)

def getIsolateTime(judgeNum, settings):
    try:
        meta = None
        t = -1
        mem = -1
        exitcode = -1
        try:
            meta = open("Judge" + str(judgeNum) + "/meta.yaml", "r")
        except:
            return (-1, -1, -1)
        for line in meta:
            if line.startswith("time"):
                t = float(line[line.find(":") + 1:].strip())
            elif line.startswith("cg-mem"):
                mem = float(line[line.find(":") + 1:].strip())
            elif line.startswith("exit"):
                exitcode = int(line[line.find(":") + 1:].strip())
        meta.close()
        return (t, mem, exitcode)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        with open("InternalErrors.txt", "w") as f:
            f.write(str(exc_type) + " " + str(fname) + " " + str(exc_tb.tb_lineno) + "\n")
            f.flush()
            f.close()

def get_public_class(submission_contents):
    for line in submission_contents.split("\n"):
        arr = line.split()
        for i in range(len(arr) - 2):
            if arr[i] == "public" and arr[i + 1] == "class":
                name = ""
                for chr in range(len(arr[i + 2])):
                    if arr[i + 2][chr] == "{":
                        break
                    name += arr[i + 2][chr]
                return name
    return None

def judge(problem, bat, case, compl, cmdrun, judgeNum, timelim, username, sc, settings):
    try:
        if case == 1:
            anyErrors = open("Judge" + str(judgeNum) + "/errors.txt", "w")
            stdout = open("Judge" + str(judgeNum) + "/stdout.txt", "w")

            comp = subprocess.Popen(compl, stdout=stdout, stderr=anyErrors, shell=True)

            try:
                comp.wait(timeout = compTimeout)
                anyErrors.flush()
                anyErrors.close()
                stdout.flush()
                stdout.close()
            except subprocess.TimeoutExpired:
                return ("Compilation Error: Request timed out", 0, 0)

            if not comp.poll() == 0:
                return ("Compilation Error (See error messages below)", 0, 0)

        write_file(sc, problem, bat, case, "in", "Judge" + str(judgeNum) + "/data.in")

        myInput = open("Judge" + str(judgeNum) + "/data.in", "r")
        myOutput = open("Judge" + str(judgeNum) + "/data.out", "w")
        anyErrors = open("errors.txt", "w")
        
        ts = "{x:.3f}".format(x = timelim)

        try:
            proc = subprocess.Popen(cmdrun, stdin=myInput, stdout=myOutput, stderr=anyErrors, shell=True)
            proc.wait(timelim + 3) # Add 3 seconds of grace time
        except subprocess.TimeoutExpired:
            return ("Time Limit Exceeded [>" + str(ts) + " seconds]", timelim, 0)

        getIsolate = getIsolateTime(judgeNum, settings)
        ft = getIsolate[0]
        fm = getIsolate[1]
        exitcode = getIsolate[2]

        # Cleanup sandbox and output files
        os.system("isolate --cg --cleanup > /dev/null && isolate --cg --init > /dev/null")

        taken = "{x:.3f}".format(x = ft)

        poll = proc.poll()
        proc.terminate()
        myInput.close()
        myOutput.flush()
        anyErrors.flush()
        myOutput.close()
        anyErrors.close()

        memTaken = fm / 1024

        memMsg = ""
        if fm >= 1024:
            memMsg = ", {x:.2f} MB".format(x = fm / 1024) # Convert from KB to MB
        elif fm >= 0:
            memMsg = ", {x:.2f} KB".format(x = fm)

        if exitcode == -1:
            return ("Time Limit Exceeded [>" + str(ts) + " seconds]", ft, memTaken)
        elif exitcode == 9:
            return ("Memory Limit Exceeded [" + taken + " seconds" + memMsg + "]", ft, memTaken)
        elif not exitcode == 0:
            return ("Runtime Error (Exit code " + str(exitcode) + ") [" + taken + " seconds]", ft, memTaken)

        try:
            res = checkEqual(problem, bat, case, judgeNum, sc)
            verdict = "ACCEPTED" if res[0] else "Output incorrect"
            return (f"{verdict} [" + taken + " seconds" + memMsg + "]", ft, memTaken, res[1])
        except Exception as e:
            print("Fatal error during grading:\n", str(e))
            if "ERRORS_WEBHOOK" in os.environ:
                requests.post(os.environ['ERRORS_WEBHOOK'], json = {"content":f"{os.environ.get('PING_MESSAGE')}\n**Error occured on judge {judgeNum}:**\n```{traceback.format_exc()}```"})
            return ("Internal System Error [" + taken + " seconds" + memMsg + "]", ft, memTaken)
    except Exception as e:
        if "ERRORS_WEBHOOK" in os.environ:
            requests.post(os.environ['ERRORS_WEBHOOK'], json = {"content":f"{os.environ.get('PING_MESSAGE')}\n**Error occured on judge {judgeNum}:**\n```{traceback.format_exc()}```"})

    os.system("rm Judge" + str(judgeNum) + "/data.out")