#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# License: GNU LGPL v3
"""
Get Unify's extranet timetables

<<<<<<< HEAD
Usage: timetable [-h] [-l] [-j] [-m] [-s] [-u url] [-f FILE] [PERIOD]
=======
Usage: timetable [-h] [-j] [-c] [-m] [-s] [-u url] [-f FILE] [PERIOD]
>>>>>>> c7a3cc1ae9ca569e13044d6acd14ad5eb827911b

Arguments:
    PERIOD     Prints timetable for a given period
               Default is to print all available informations
               See the examples below for more precisions

Options:
    -h, --help          Print this help and exit
    -j, --json          Print data in the JSON format
    -c, --compact       Use a compact output format
    -m, --manual        Do not use automatic login
    -s, --save          Save password to keyring.
                        Needs to be combined with --manual
    -u, --url URL       Url of Unify's extranet
                        Default is in '~/.extranet'
    -f, --file FILE     Use FILE to find credential
                        Default is in '~/.extranet'

Examples:
    timetable  0        : print the current course
    timetable  n        : print n next courses
    timetable  today    : print today's courses
    timetable  tomorrow : print tomorrow's courses
    timetable  first    : print tomorrow's first course
    timetable  next     : print the next course
    timetable  previous : print the previous course
    timetable  current  : print the current course
    timetable  dd/mm    : print the courses of given date
"""

import os
import re
import sys
import time
import datetime
import getpass
from docopt import docopt
from extranet import Extranet
from extranet.exceptions import *
import keyring


# To use french names
# DAYS   = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
# MONTHS = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin",
#          "Juil", "Aou", "Sep", "Oct", "Nov", "Dec"]

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def print_courses(courses, *, compact=False, fmt=None):
    if fmt is None:
        if compact:
            fmt = "{title}: {period}: {room}"
        else:
            fmt = "{title}\n    {room}\n    {period}\n"

    for c in courses:
        print(fmt.format(title=c["title"],
                         room=c["room"],
                         period=period(c["start"], c["end"])))

def period(start, end, *, days=DAYS, months=MONTHS):
    return "{wday} {day} {mon}:\033[1;33m{sh}h{sm}-{eh}h{em}\033[1;m".format(
        wday=days[int(start.weekday())],
        day=start.day,
        mon=months[int(start.month) - 1],
        sh=start.hour,
        sm=start.minute,
        eh=end.hour,
        em=end.minute)

def inline_period(start):
    return "{day}/{mon}: {sh}h{sm}".format(
        day=start.day,
        mon=start.month,
        sh=start.hour,
        sm=start.minute)


def now():
    return datetime.datetime.fromtimestamp(time.time())


# This function cannot be considered stable at this time, use with caution
def courses_in_range(start, end, num, timetable):
    """
    start and end may be a timestamp, "start" or "end"
    where "start" and "end" will refer to the corresponding time
    of the courses.

    num is the maximum number of results wanted.
    """
    result = []
    start_lim = start
    end_lim = end

    for course in timetable:
        if num == 0:
            break

        if type(start) == str:
            start_lim = course[start].timestamp()

        if type(end) == str:
            end_lim = course[end].timestamp()

        if start_lim < now().timestamp() <= end_lim:
            result.append(course)
            num -= 1

    return result


def filter_dates(timetable, selection):
    if selection is None:
        return timetable

    if selection == "previous":
        timetable.reverse()
        return courses_in_range("end", now().timestamp(), 1, timetable)

    if selection == "current" or selection == "0":
        return courses_in_range("start", "end", 1, timetable)

    if selection == "next":
        return courses_in_range(0, "start", 1, timetable)

    if selection == "today":
        return [x for x in timetable
                if x["start"].day == now().day]

    if selection == "tomorrow":
        return [x for x in timetable
                if x["start"].day == (now().day + 1)]

    if selection == "first":
        return [x for x in timetable
                if x["start"].day == (now().day + 1)][:1]

    if re.match(r"[0-9]+$", selection):
        n = int(selection)
        return courses_in_range(0, "start", n, timetable)

    if re.match(r"[0-9]{1,2}/[0-9]{1,2}$", selection):
        selected = selection.split("/")
        return [x for x in timetable
                if x["start"].day == int(selected[0])
                and x["start"].month == int(selected[1])]

    else:
        sys.exit("Invalid command: " + selection)


def converted_dates(timetable):
    for course in timetable:
        course["start"] = course["start"].timestamp()
        course["end"] = course["end"].timestamp()

    return timetable


def main():
    args = docopt(__doc__)

    cred_file = args["--file"] or "%s/.extranet" % os.environ["HOME"]

    if not os.path.exists(cred_file):
        open(cred_file, 'w').close()

    if args["--manual"]:
        url = input("Unify's extranet url: ")
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        if args["--save"]:
            with open(cred_file, 'w') as f:
                f.write(username + "\n" + url + "\n")
                keyring.set_password("extranet", username + url, password)

    else:
        with open(cred_file) as f:
            username, url = f.read().splitlines()
            password = keyring.get_password("extranet", username + url)

    try:
        timetable = Extranet(url, username, password).get_timetable()
    except LoginError:
        exit("Wrong login\n"
             + "If no password has been saved yet, please, try:\n"
             + "    timetable.py -ms")

    except ConnectionError:
        exit("Cannot establish a connection to server")

    except FatalError:
        exit("An unexpected error happened")

    except ValueError as e:
        exit("If no password has been saved yet, please, try:\n"
             + "    timetable.py -ms")

    # Sort timetable chronologically
    timetable.sort(key=lambda x: x["start"].timestamp())

    timetable = filter_dates(timetable, args["PERIOD"])

    if args["--json"]:
        print(converted_dates(timetable))
    else:
        print_courses(timetable, compact=args["--compact"])


if __name__ == "__main__":
    main()
