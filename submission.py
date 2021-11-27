import judging
import math
import asyncio
import os
import sys

def writeCode(source, filename):
    f = open(filename, "w")
    f.write(source)
    f.close()
    
def clean(src):
    return src.replace("`", "")

def edit(settings, content, judgeNum):
    settings.update_one({"type":"judge", "num":judgeNum}, {"$set":{"output":content}})

def submit(storage_client, settings, username, source, lang, problem, judgeNum, attachment, lang_dict) -> int:
    try:
        settings.insert_one({"type":"use", "author":username, "message":source})
        filename = lang_dict[2]
        
        cleaned = ""
        if attachment:
            url = source
            os.system("wget " + url + " -Q10k --timeout=3 -O " + "Judge" + str(judgeNum) + "/" + filename)
        else:
            # Clean up code from all backticks
            cleaned = clean(source)
            writeCode(cleaned, "Judge" + str(judgeNum) + "/" + filename)

        judging.get_file(storage_client, "TestData/" + str(problem) + "/cases.txt", "Judge" + str(judgeNum) + "/cases.txt")
        problemData = open("Judge" + str(judgeNum) + "/cases.txt", "r")

        batches = list(map(int, problemData.readline().split()))
        extra = False
        for x in batches:
            if x >= 10:
                extra = True
                break
        if len(batches) >= 10:
            extra = True

        points = list(map(int, problemData.readline().split()))

        timelims = list(map(float, problemData.readline().split()))
        timelim = None

        id = settings.find_one({"type":"lang", "name":lang})['id']

        if len(timelims) == 1:
            timelim = timelims[0]
        else:
            timelim = timelims[id]

        inds = problemData.readline()
        individual = False
        if len(inds) > 0:
            arr = inds.split()
            individual = arr[id].strip() == 'T'

        problemData.close()

        msg = "EXECUTION RESULTS\n" + username + "'s submission for " + problem + " in " + lang + "\n" + ("Time limit for this problem in " + lang + ": {x:.2f} seconds".format(x = timelim)) + "\nRunning on Judging Server #" + str(judgeNum) + "\n\n"
        curmsg = ("```" + msg + "(Status: COMPILING)```")
        
        edit(settings, curmsg, judgeNum)

        localPath = settings.find_one({"type":"judge", "num":judgeNum})['path']
        compl = lang_dict[0].format(x = judgeNum, path = localPath)
        cmdrun = lang_dict[1].format(x = judgeNum, t = timelim, path = localPath)

        finalscore = 0
        ce = False

        b = 0
        tot = sum(batches)
        interval = int(math.ceil(tot / 4))
        cnt = 0

        totalTime = 0
        processMem = 0

        if tot > 20:
            interval //= 2

        while b < len(batches):
            sk = False
            batmsg = ""
            verd = ""

            if tot <= 20:
                for i in range(1, batches[b] + 1):
                    verd = ""
                    if not sk:
                        vv = judging.judge(problem, b + 1, i, compl, cmdrun, judgeNum, timelim, username, storage_client, settings)
                        verd = vv[0]
                        totalTime += vv[1]
                        processMem = max(processMem, vv[2])

                    if not sk and verd.split()[0] == "Compilation":
                        comp = open("Judge" + str(judgeNum) + "/errors.txt", "r")
                        pe = open("Judge" + str(judgeNum) + "/stdout.txt", "r")
                        msg += "- " + verd + "\n" + comp.read(1000)
                        psrc = pe.read(1000)
                        if len(psrc) > 0:
                            msg += "\n" + psrc
                        msg += "\n"
                        comp.close()
                        pe.close()
                        ce = True
                        break

                    if not sk and verd.split()[0] == "Judging":
                        msg += verd + "\n"

                    batmsg += ("+" if verd.split()[0] == "Accepted" else "-") + "     Case #" + str(i) + ": " + (" " if (extra and i < 10) else "") + verd + "\n"
                    if verd.split()[0] != "Accepted":
                        for x in range(i + 1, batches[b] + 1):
                            batmsg += "      Case #" + str(x) + ": " + (" " if (extra and x < 10) else "") + "--\n"
                        sk = True

                    if sk and batches[b] > 1:
                        #if batches[b] > 1:
                        edit(settings, ("```diff\n" + msg + "- Batch #" + str(b + 1) + " (0/" + str(points[b]) + " points)\n" + batmsg + "\n(Status: RUNNING)```"), judgeNum)
                        #else:
                            #await curmsg.edit(content = ("```diff\n" + msg + "- Test case #" + str(b + 1) + ": " + (" " if extra else "") + verd + " (0/" + str(points[b]) + " points)\n\n(Status: RUNNING)```"))
                        break
                    else:
                        if batches[b] > 1:
                            edit(settings, ("```diff\n" + msg + "+ Batch #" + str(b + 1) + " (" + str(points[b]) + "/" + str(points[b]) + " points)\n" + batmsg + "\n(Status: RUNNING)```"), judgeNum)
                        else:
                            if sk:
                                edit(settings, ("```diff\n" + msg + "- Test case #" + str(b + 1) + ": " + (" " if (extra and b < 9) else "") + verd + " (0/" + str(points[b]) + " points)\n\n(Status: RUNNING)```"), judgeNum)
                            else:
                                edit(settings, ("```diff\n" + msg + "+ Test case #" + str(b + 1) + ": " + (" " if (extra and b < 9) else "") + verd + " (" + str(points[b]) + "/" + str(points[b]) + " points)\n\n(Status: RUNNING)```"), judgeNum)

                        cnt += 1
            else:
                tt = 0
                avgMem = 0
                for i in range(1, batches[b] + 1):
                    edit(settings, ("```diff\n" + msg + "  Batch #" + str(b + 1) + " (?/" + str(points[b]) + " points)\n      Pending judgement on case " + str(i) + "\n\n(Status: RUNNING)```"), judgeNum)

                    verd = ""
                    if not sk:
                        vv = judging.judge(problem, b + 1, i, compl, cmdrun, judgeNum, timelim, username, storage_client, settings)
                        verd = vv[0]
                        tt += vv[1]
                        avgMem += vv[2]

                        totalTime += vv[1]
                        processMem = max(processMem, vv[2])

                    if not sk and verd.split()[0] == "Compilation":
                        comp = open("Judge" + str(judgeNum) + "/errors.txt", "r")
                        pe = open("Judge" + str(judgeNum) + "/stdout.txt", "r")
                        msg += "- " + verd + "\n" + comp.read(1000)
                        psrc = pe.read(1000)
                        if len(psrc) > 0:
                            msg += "\n" + psrc
                        msg += "\n"
                        comp.close()
                        pe.close()
                        ce = True
                        break

                    if not verd.startswith("Accepted"):
                        edit(settings, ("```diff\n" + msg + "  Batch #" + str(b + 1) + " (?/" + str(points[b]) + " points)\n-     " + verd[:(verd.index("["))] + "on case " + str(i) + " " + verd[(verd.index("[")):] + "\n\n(Status: RUNNING)```"), judgeNum)
                        msg += "  Batch #" + str(b + 1) + " (0/" + str(points[b]) + " points)\n-     " + verd[:(verd.index("["))] + "on case " + str(i) + " " + verd[(verd.index("[")):] + "\n\n"
                        sk = True
                        cnt += 1
                        break

                    cnt += 1
                
                if not sk and not ce:
                    msg += "+ Batch #" + str(b + 1) + " (" + str(points[b]) + "/" + str(points[b]) + " points)\n" + "+     All cases passed (" + str(batches[b]) + " cases in " + "{x:.3f}s, {m:.2f} MB)".format(x = tt, m = avgMem / batches[b]) + "\n\n"
                    finalscore += points[b]

            if ce:
                break
            if tot > 20:
                b += 1
                continue
            if not sk:
                finalscore += points[b]
                if batches[b] == 1:
                    msg += "+ Test case #" + str(b + 1) + ": " + (" " if (extra and b < 9) else "") + verd + " (" + str(points[b]) + "/" + str(points[b]) + " points)\n"
                else:
                    msg += "+ Batch #" + str(b + 1) + " (" + str(points[b]) + "/" + str(points[b]) + " points)\n" + batmsg + "\n"
            else:
                if batches[b] == 1:
                    msg += "- Test case #" + str(b + 1) + ": " + (" " if (extra and b < 9) else "") + verd + " (0/" + str(points[b]) + " points)\n"
                else:
                    msg += "- Batch #" + str(b + 1) + " (0/" + str(points[b]) + " points)\n" + batmsg + "\n"
            b += 1
        
        if batches[len(batches) - 1] == 1:
            msg += "\n"
        msg += "\nFinal Score: " + str(finalscore) + " / 100\nExecution finished using {taken:.3f} seconds, {mem:.2f} MB".format(taken = totalTime, mem = processMem)
        edit(settings, ("```diff\n" + msg + "\n(Status: COMPLETED)```"), judgeNum)

        finalOutput = ("```diff\n" + msg + "\n(Status: COMPLETED)```")
        if ce:
            return (-1, finalOutput)
            
        return (finalscore, finalOutput)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        with open("InternalErrors.txt", "w") as f:
            f.write(str(exc_type) + " " + str(fname) + " " + str(exc_tb.tb_lineno) + "\n")
            f.flush()
            f.close()