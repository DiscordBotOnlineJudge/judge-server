import judging
import math
import yaml
import asyncio
import os
import sys
import contests

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

        lang_data = settings.find_one({"type":"lang", "name":lang})
        filename = lang_data['filename']
        
        cleaned = ""
        if attachment:
            url = source
            os.system("wget " + url + " -Q10k --timeout=3 -O " + "Judge" + str(judgeNum) + "/" + filename)
        else:
            # Clean up code from all backticks
            cleaned = clean(source)
            writeCode(cleaned, "Judge" + str(judgeNum) + "/" + filename)

        judging.get_file(storage_client, "TestData/" + str(problem) + "/cases.txt", "Judge" + str(judgeNum) + "/cases.txt")
        judging.get_file(storage_client, "TestData/" + str(problem) + "/resources.yaml", "Judge" + str(judgeNum) + "/resources.yaml")
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
        resources = yaml.safe_load(open("Judge" + str(judgeNum) + "/resources.yaml", "r").read())

        timelim = resources['time-limit']['general']
        if lang in resources['time-limit']:
            timelim = resources['time-limit'][lang]

        memlim = resources['memory-limit']['general']
        if lang in resources['memory-limit']:
            memlim = resources['memory-limit'][lang]

        problemData.close()

        msg = "EXECUTION RESULTS\n" + username + "'s submission for " + problem + " in " + lang + "\n" + ("Time limit in " + lang + ": {x:.2f} seconds, ".format(x = timelim)) + ("Memory limit in " + lang + ": " + str(memlim // 1024) + " MB") + "\nRunning on Judging Server #" + str(judgeNum) + "\n\n"
        curmsg = ("```" + msg + "(Status: COMPILING)```")
        
        edit(settings, curmsg, sub_id)

        localPath = os.getcwd()
        compl = lang_data['compl'].format(x = judgeNum, path = localPath)
        cmdrun = lang_data['run'].format(x = judgeNum, t = timelim, path = localPath, mem = memlim)

        public_class = None

        if lang == "java":
            public_class = judging.get_public_class(open("Judge" + str(judgeNum) + "/java/Main.java", "r").read())
            if public_class is None:
                finalOutput = "```diff\n" + msg + "- Compilation Error: Public class not found.\n  Please declare your main class as a public class.\n\n\n(Status: COMPLETED)```"
                edit(settings, finalOutput, sub_id)
                return (0, finalOutput)
            os.system("mv " + "Judge" + str(judgeNum) + "/java/Main.java " + "Judge" + str(judgeNum) + "/java/" + public_class + ".java")
            compl = compl.replace("Main.java", public_class + ".java")
            cmdrun = cmdrun.replace("Main", public_class)
        else:
            public_class = ""

        finalscore = 0
        ce = False

        b = 0
        tot = sum(batches)
        interval = int(math.ceil(tot / 4))
        cnt = 0

        totalTime = 0
        processMem = 0

        if tot > THRESHOLD:
            interval //= 2

        while b < len(batches):
            sk = False
            batmsg = ""
            verd = ""

            if tot <= THRESHOLD:
                for i in range(1, batches[b] + 1):
                    verd = ""
                    if not sk and not public_class is None:
                        vv = judging.judge(problem, b + 1, i, compl, cmdrun, judgeNum, timelim, username, storage_client, settings)
                        verd = vv[0]
                        totalTime += vv[1]
                        processMem = max(processMem, vv[2])

                    if not sk and (public_class is None or verd.split()[0] == "Compilation"):
                        comp = open("Judge" + str(judgeNum) + "/errors.txt", "r")
                        pe = open("Judge" + str(judgeNum) + "/stdout.txt", "r")
                        msg += "- " + verd + "\n" + comp.read(1700)
                        psrc = pe.read(1700)
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
                        edit(settings, ("```diff\n" + msg + "- Batch #" + str(b + 1) + " (0/" + str(points[b]) + " points)\n" + batmsg + "\n(Status: RUNNING)```"), sub_id)
                        break
                    else:
                        if batches[b] > 1:
                            edit(settings, ("```diff\n" + msg + "+ Batch #" + str(b + 1) + " (" + str(points[b]) + "/" + str(points[b]) + " points)\n" + batmsg + "\n(Status: RUNNING)```"), sub_id)
                        else:
                            if sk:
                                edit(settings, ("```diff\n" + msg + "- Test case #" + str(b + 1) + ": " + (" " if (extra and b < 9) else "") + verd + " (0/" + str(points[b]) + " points)\n\n(Status: RUNNING)```"), sub_id)
                            else:
                                edit(settings, ("```diff\n" + msg + "+ Test case #" + str(b + 1) + ": " + (" " if (extra and b < 9) else "") + verd + " (" + str(points[b]) + "/" + str(points[b]) + " points)\n\n(Status: RUNNING)```"), sub_id)

                        cnt += 1
            else:
                tt = 0
                avgMem = 0
                for i in range(1, batches[b] + 1):
                    edit(settings, ("```diff\n" + msg + "  Batch #" + str(b + 1) + " (?/" + str(points[b]) + " points)\n      Pending judgement on case " + str(i) + "\n\n(Status: RUNNING)```"), sub_id)

                    verd = ""
                    if not sk and not public_class is None:
                        vv = judging.judge(problem, b + 1, i, compl, cmdrun, judgeNum, timelim, username, storage_client, settings)
                        verd = vv[0]
                        tt += vv[1]
                        avgMem += vv[2]

                        totalTime += vv[1]
                        processMem = max(processMem, vv[2])

                    if not sk and (public_class is None or verd.split()[0] == "Compilation"):
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
            if tot > THRESHOLD:
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

        os.system("rm -r Judge" + str(judgeNum) + "/java/*") # Remove all java files and classes
        
        if batches[len(batches) - 1] == 1:
            msg += "\n"
        msg += "\nFinal Score: " + str(finalscore) + " / 100\nExecution finished using {taken:.3f} seconds, {mem:.2f} MB".format(taken = totalTime, mem = processMem)
        edit(settings, ("```diff\n" + msg + "\n(Status: COMPLETED)```"), sub_id)

        finalOutput = ("```diff\n" + msg + "\n(Status: COMPLETED)```")
        if ce:
            return (-1, finalOutput)
            
        problm = settings.find_one({"type":"problem", "name":problem})

        if finalscore == 100:
            contests.addToProfile(settings, username, problem)

        if len(problm['contest']) > 0 and finalscore >= 0:
            contests.updateScore(settings, problm['contest'], problem, username, finalscore, ct)

        return (finalscore, finalOutput)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        with open("InternalErrors.txt", "w") as f:
            f.write(str(exc_type) + " " + str(fname) + " " + str(exc_tb.tb_lineno) + "\n")
            f.flush()
            f.close()

        edit(settings, "```diff\n- Internal error occurred on Judge " + str(judgeNum) + "\n\n(Status: COMPLETED)```", sub_id)
        return (-1, "```diff\n- Internal error occurred on Judge " + str(judgeNum) + "\n\n(Status: COMPLETED)```")
