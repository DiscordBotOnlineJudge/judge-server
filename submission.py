import judging
import math
import yaml
import asyncio
import os
import sys
import contests
import requests, traceback

THRESHOLD = 30

def writeCode(source, filename):
    f = open(filename, "w")
    f.write(source)
    f.close()
    
def clean(src):
    return src.replace("`", "")

def edit(settings, content, sub_id):
    settings.update_one({"type":"submission", "id":sub_id}, {"$set":{"output":content}})

def submit(storage_client, settings, username, source, lang, problem, judgeNum, attachment, sub_id) -> int:
    try:
        ct = contests.current_time()

        lang_data = settings.find_one({"type":"tej-lang", "name":lang})
        filename = lang_data['filename']
        
        cleaned = ""
        if attachment:
            url = source
            os.system("wget " + url + " -Q10k --timeout=3 -O " + "Judge" + str(judgeNum) + "/" + filename)
        else:
            # Clean up code from all backticks
            cleaned = clean(source)
            writeCode(cleaned, "Judge" + str(judgeNum) + "/" + filename)

        judging.get_file(storage_client, "TestData/" + str(problem) + "/resources.yaml", "Judge" + str(judgeNum) + "/resources.yaml")
        resources = yaml.safe_load(open("Judge" + str(judgeNum) + "/resources.yaml", "r").read())

        cases = resources['cases']

        msg = "EXECUTION RESULTS\n" + username + "'s submission for C-Lang Part " + problem + " in " + lang + "\nRunning on Judging Server #" + str(judgeNum) + "\n\n"
        curmsg = ("```" + msg + "(Status: COMPILING)```")
        
        edit(settings, curmsg, sub_id)

        localPath = os.getcwd()
        compl = lang_data['compl'].format(x = judgeNum, path = localPath)
        cmdrun = lang_data['run'].format(x = judgeNum, t = 5, path = localPath, mem = 262144)

        finalscore = "CORRECT"
        ce = False

        totalTime = 0
        processMem = 0

        for case in range(1, cases + 1):
            verdict = judging.judge(problem, 1, case, compl, cmdrun, judgeNum, 3, username, storage_client, settings)
            msg += (f"  Test case #{case}: ") + verdict[0] + "\n"

            if verdict[0].startswith("Compilation Error"):
                msg += open(f"Judge{judgeNum}/errors.txt", "r").read(500) + "\n"
                finalscore = "failed one or more tests"
                settings.update_one({"type":"submission", "id":sub_id}, {"$set":{"status":"Incorrect"}})
                break

            if len(verdict) == 4:
                msg += f"----------Feedback----------\n{verdict[3]}\n----------------------------\n\n\n"
                if verdict[0].startswith("Output incorrect"):
                    finalscore = "failed one or more tests"
                    settings.update_one({"type":"submission", "id":sub_id}, {"$set":{"status":"Incorrect"}})
            else:
                finalscore = "failed one or more tests"
                settings.update_one({"type":"submission", "id":sub_id}, {"$set":{"status":"Incorrect"}})

            totalTime += verdict[1]
            processMem = max(processMem, verdict[2])

        if finalscore == "CORRECT":
            settings.update_one({"type":"submission", "id":sub_id}, {"$set":{"status":"Correct"}})
        msg += "\nFinal verdict: " + finalscore + "\nExecution finished using {taken:.3f} seconds, {mem:.2f} MB".format(taken = totalTime, mem = processMem)
        edit(settings, ("```diff\n" + msg + "\n(Status: COMPLETED)```"), sub_id)

        finalOutput = ("```diff\n" + msg + "\n(Status: COMPLETED)```")
        if ce:
            return (-1, finalOutput)
            
        problm = settings.find_one({"type":"problem", "name":problem})

        #if finalscore == 100:
        #    contests.addToProfile(settings, username, problem)

        #if len(problm['contest']) > 0 and finalscore >= 0:
        #    contests.updateScore(settings, problm['contest'], problem, username, finalscore, ct)

        return (finalscore, finalOutput)
    except Exception as e:
        if "ERRORS_WEBHOOK" in os.environ:
            requests.post(os.environ['ERRORS_WEBHOOK'], json = {"content":f"{os.environ.get('PING_MESSAGE')}\n**Error occured on judge {judgeNum}:**\n```{traceback.format_exc()}```"})

        edit(settings, "```diff\n- Internal error occurred on Judge " + str(judgeNum) + "\n\n(Status: COMPLETED)```", sub_id)
        return (-1, "```diff\n- Internal error occurred on Judge " + str(judgeNum) + "\n\n(Status: COMPLETED)```")
