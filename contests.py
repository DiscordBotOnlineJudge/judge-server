import time
import os
import subprocess
import math
import dns
from pymongo import MongoClient
from datetime import datetime
import pytz

def current_time():
    tz = pytz.timezone("America/New_York")
    return datetime.now(tz).strftime("%Y %m %d %H %M %S")

def all_equal(a, b):
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if a[i] != b[i]:
            return False
    return True

def greater_equal(x, y, i):
    if i == 5:
        return x[5] >= y[5]
    if x[i] > y[i]:
        return True
    elif x[i] < y[i]:
        return False
    else:
        return greater_equal(x, y, i + 1)

def compString(a, b):
    a = list(map(int, a.split()))
    b = list(map(int, b.split()))
    return greater_equal(a, b, 0)

def date(a, b, c):
    x = list(map(int, a.split()))
    y = list(map(int, b.split()))
    u = list(map(int, c.split()))
    return (greater_equal(u, x, 0) and greater_equal(y, u, 0))

def compare(t1, t2):
    a = list(map(int, t1.split()))
    b = list(map(int, t2.split()))

    if a[0] != b[0] or a[1] != b[1] or a[2] != b[2]:
        return 999999 # Incorrect date

    total = (b[3] - a[3]) * 3600 + (b[4] - a[4]) * 60 + (b[5] - a[5])
    return total

def perms(settings, found, author):
    acc = settings.find_one({"type":"access", "mode":found['contest'], "name":author})
    if (not settings.find_one({"type":"access", "mode":"owner", "name":author}) is None):
        return False # Has owner perms
    if (not settings.find_one({"type":"access", "mode":"admin", "name":author}) is None) and (author in found['authors']):
        return False # Has admin perms
    elif (not acc is None) and (found['status'] == "s") and contests.compare(acc['start'], contests.current_time()) <= getLen(settings, found['contest']):
        return False # Has contest participant perms
    return (not found['published']) or (found['status'] != "s")

def getLen(settings, contest):
    return settings.find_one({"type":"contest", "name":contest})['len']

def get_bonus(rem, pts):
    return (pts * rem) // 30000

def updateScore(settings, contest, problem, user, score, ct):
    post = settings.find_one({"type":"access", "name":user, "mode":contest})
    if post is None:
        print("Failed to update score (no access post)")
        return
    elapsed = compare(post['start'], ct)
    contest_len = getLen(settings, contest)
    if elapsed > contest_len:
        print("Invalid score update")
        return
    arr = post['solved']
    penalty = post['penalty']
    time_bonus = post['time-bonus']

    num = int(problem[len(problem) - 1])

    if score <= arr[num] and arr[num] < 100:
        penalty[num] += 1
    if arr[num] < 100:
        settings.update_one({"_id":post['_id']}, {"$set":{"taken":elapsed}})

    arr[num] = max(arr[num], score)
    time_bonus[num] = max(time_bonus[num], get_bonus(contest_len - elapsed, score))

    settings.update_one({"_id":post['_id']}, {"$set":{"solved":arr, "penalty":penalty, "time-bonus":time_bonus}})