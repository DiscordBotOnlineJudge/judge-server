# This file contains methods that the judge uses to determine
# a verdict for a submission test case

import time
import os
import subprocess
import math
import asyncio
import resource
import yaml
import sys

def limit_virtual_memory():
    MAX_VIRTUAL_MEMORY = 256 * 1024 * 1024 # MB
    resource.setrlimit(resource.RLIMIT_AS, (MAX_VIRTUAL_MEMORY, resource.RLIM_INFINITY))

def cleanChecker(fn, jn):
    f = open(fn, "r")
    src = f.read().replace("data.in", "Judge" + jn + "/data.in").replace("data.out", "Judge" + jn + "/data.out")
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
            v = f.read().strip() == "AC"
            f.close()
            return v

    except:
        write_file(storage_client, problem, bat, case, "out", "Judge" + str(judgeNum) + "/expected.out")

        cor = open("Judge" + str(judgeNum) + "/expected.out", "r")
        giv = open("Judge" + str(judgeNum) + "/data.out", "r")

        expect = cor.read()
        mine = giv.read()

        giv.flush()
        giv.close()
        cor.flush()
        cor.close()

        return cleanNullChars(expect).strip() == cleanNullChars(mine).strip()

def get_file(storage_client, blobname, save):
    blob = storage_client.blob(blobname)
    blob.download_to_filename(save)

def write_file(storage_client, problem, bat, case, ext, save):
    blob = storage_client.blob("TestData/" + problem + "/data" + str(bat) + "." + str(case) + "." + ext)
    blob.download_to_filename(save)

def getIsolateTime(judgeNum, settings):
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
        elif line.starswith("exitcode"):
            exitcode = int(line[line.find(":") + 1:].strip())
    meta.close()
    return (t, mem, exitcode)

def judge(problem, bat, case, compl, cmdrun, judgeNum, timelim, username, sc, settings):
    try:
        if bat <= 1 and case <= 1 and len(compl) > 0:
            anyErrors = open("Judge" + str(judgeNum) + "/errors.txt", "w")
            stdout = open("Judge" + str(judgeNum) + "/stdout.txt", "w")
            comp = subprocess.Popen(compl, stdout=stdout, stderr=anyErrors, shell=True)

            try:
                comp.wait(timeout = 5)
                anyErrors.flush()
                anyErrors.close()
                stdout.flush()
                stdout.close()
            except subprocess.TimeoutExpired:
                return ("Compilation Error: Request timed out", 0, 0)

            if not comp.poll() == 0:
                return ("Compilation Error", 0, 0)

        write_file(sc, problem, bat, case, "in", "Judge" + str(judgeNum) + "/data.in")

        myInput = open("Judge" + str(judgeNum) + "/data.in", "r")
        myOutput = open("Judge" + str(judgeNum) + "/data.out", "w")
        anyErrors = open("errors.txt", "w")
        
        proc = subprocess.Popen(cmdrun, stdin=myInput, stdout=myOutput, stderr=anyErrors, shell=True)
        proc.wait(timelim + 3) # Add 3 seconds of grace time

        getIsolate = getIsolateTime(judgeNum, settings)
        ft = getIsolate[0]
        fm = getIsolate[1]
        exitcode = getIsolate[2]
        os.system("isolate --cg --cleanup > /dev/null && isolate --cg --init > /dev/null")

        taken = "{x:.3f}".format(x = ft)

        poll = proc.poll()
        proc.terminate()
        myInput.close()
        myOutput.flush()
        anyErrors.flush()
        myOutput.close()
        anyErrors.close()

        ts = "{x:.3f}".format(x = timelim)
        memTaken = fm / 1024

        if exitcode == -1:
            return ("Time Limit Exceeded [>" + str(ts) + " seconds]", ft, memTaken)
        elif not exitcode == 0:
            return ("Runtime/Memory Error (Exit code " + str(poll) + ") [" + taken + " seconds]", ft, memTaken)
        
        memMsg = ""
        if fm >= 1000:
            memMsg = ", {x:.2f} MB".format(x = fm / 1024) # Convert from KB to MB
        elif fm >= 0:
            memMsg = ", {x:.2f} KB".format(x = fm)

        try:
            if checkEqual(problem, bat, case, judgeNum, sc):
                return ("Accepted [" + taken + " seconds" + memMsg + "]", ft, memTaken)
            else:
                return ("Wrong Answer [" + taken + " seconds" + memMsg + "]", ft, memTaken)
        except Exception as e:
            print("Fatal error during grading:\n", str(e))
            return ("Internal System Error [" + taken + " seconds" + memMsg + "]", ft, memTaken)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        with open("InternalErrors.txt", "w") as f:
            f.write(str(exc_type) + " " + str(fname) + " " + str(exc_tb.tb_lineno) + "\n")
            f.flush()
            f.close()
