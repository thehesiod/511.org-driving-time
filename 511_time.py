#!/usr/bin/env python3
import requests
import xmltodict
import copy
import time
import argparse
import readline
import pprint

if 'libedit' in readline.__doc__:
    readline.parse_and_bind("bind -e")
    readline.parse_and_bind("bind '\t' rl_complete")
else:
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims('')


class Completer(object):
    def __init__(self, options):
        self._options = sorted(options)
        self._matches = []
        return

    def complete(self, text, state):
        results = [s for s in self._options if s and s.startswith(text)] + [None]
        return results[state]


def tab_complete(prompt, options):
    if len(options) == 1: return options[0]

    c = Completer(options)
    readline.set_completer(c.complete)

    print("Please select from Available options:", pprint.pformat(sorted(options)))
    line = ''
    while line not in options:
        line = input(prompt)

    return line


def main():
    parser = argparse.ArgumentParser(description='Script which periodically checks the minimum time between two points')
    parser.add_argument("-token", required=True, help="511.org API token")
    parser.add_argument("-period", type=int, default=60, help="Number of seconds between refreshes")
    parser.add_argument("-origin", help="origin, ex: San Carlos/US-101 S/HOLLY ST")
    parser.add_argument("-dest", help="destination, ex: San Jose/US-101 S/HOLLY ST")
    parser.add_argument("-verbose", action='store_true', help="Verbose Output")
    app_args = parser.parse_args()

    token_obj = {"token": app_args.token}

    origins = requests.get('http://services.my511.org/traffic/getoriginlist.aspx', params=token_obj)
    assert origins.status_code == 200
    origins = xmltodict.parse(origins.text)
    origins = origins["origins"]["origin"]

    if not app_args.origin:
        options = [o["city"] + "/" + o["mainRoad"] + "/" + o["crossRoad"] for o in origins]
        app_args.origin = tab_complete("Please Select Origin: ", options)

    app_args.origin = app_args.origin.split("/")

    origins = list(filter(lambda x: x["city"] == app_args.origin[0], origins))

    origin_obj = copy.copy(token_obj)

    for o in origins:
        if o["mainRoad"] == app_args.origin[1] and o["crossRoad"] == app_args.origin[2]:
            origin_obj["o"] = o["node"]
            break

    if "o" not in origin_obj:
        raise Exception("Unable to find origin")

    destinations = requests.get('http://services.my511.org/traffic/getdestinationlist.aspx', params=origin_obj)
    assert destinations.status_code == 200
    destinations = xmltodict.parse(destinations.text)
    destinations = destinations["destinations"]["destination"]

    if not app_args.dest:
        options = [o["city"] + "/" + o["mainRoad"] + "/" + o["crossRoad"] for o in destinations]
        app_args.dest = tab_complete("Please Select Destination: ", options)

    app_args.dest = app_args.dest.split("/")

    destinations = list(filter(lambda x: x["city"] == app_args.dest[0], destinations))

    dest_obj = copy.copy(origin_obj)

    for d in destinations:
        if d["mainRoad"] == app_args.dest[1] and d["crossRoad"] == app_args.dest[2]:
            dest_obj["d"] = d["node"]
            break

    if "d" not in dest_obj:
        raise Exception("Unable to find destination")

    last_time = 0
    while True:
        paths = requests.get('http://services.my511.org/traffic/getpathlist.aspx', params=dest_obj)
        assert paths.status_code == 200
        paths = xmltodict.parse(paths.text)
        paths = paths["paths"]["path"]

        times = list(map(lambda x: x["currentTravelTime"], paths))
        min_time = min(times)

        if min_time != last_time:
            print("current travel time:", min_time, "m")
            last_time = min_time

        time.sleep(app_args.period)

if __name__ == '__main__':
    main()
