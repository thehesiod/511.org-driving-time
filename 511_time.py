#!/usr/bin/env python3
import requests
import xmltodict
import copy
import time
import argparse
import readline
import pprint
import sys

if sys.platform == "darwin":
    import Foundation
    from Foundation import NSUserNotification, NSUserNotificationCenter
    from PyObjCTools import AppHelper

    # TBD: Add windows/linux support
    class OSNotification(Foundation.NSObject):
        # Based on http://stackoverflow.com/questions/12202983/working-with-mountain-lions-notification-center-using-pyobjc

        def clearNotifications(self):
            """Clear any displayed alerts we have posted. Requires Mavericks."""

            NSUserNotificationCenter.defaultUserNotificationCenter().removeAllDeliveredNotifications()

        def notify(self, title, subtitle, text):
            """Create a user notification and display it."""

             # if appImage:
             #    source_img = AppKit.NSImage.alloc().initByReferencingFile_(appImage)
             #    notification.set_identityImage_(source_img)
             # if contentImage:
             #    source_img = AppKit.NSImage.alloc().initBy
            #     notification.setContentImage_(source_img)

            notification = NSUserNotification.alloc().init()
            notification.setTitle_(str(title))
            notification.setSubtitle_(str(subtitle))
            notification.setInformativeText_(str(text))
            notification.setSoundName_("NSUserNotificationDefaultSoundName")

            # notification.set_showsButtons_(True)
            # notification.setHasActionButton_(True)
            # notification.setHasReplyButton_ (True) # this will allow the user to enter text to "reply"
            # notification.setActionButtonTitle_("View")
            # notification.setUserInfo_({"action":"open_url", "value":url})

            NSUserNotificationCenter.defaultUserNotificationCenter().setDelegate_(self)
            NSUserNotificationCenter.defaultUserNotificationCenter().scheduleNotification_(notification)

            # Note that the notification center saves a *copy* of our object.
            AppHelper.runConsoleEventLoop()

        def userNotificationCenter_didDeliverNotification_(self, center, notification):
            AppHelper.stopEventLoop()

        # We'll get this if the user clicked on the notification.
        def userNotificationCenter_didActivateNotification_(self, center, notification):
            # this is for "reply" button
            #response = notification.response().string()

            #userInfo = notification.userInfo()
            # if userInfo["action"] == "open_url":
            pass

    def notify(title, subtitle, text):
        n = OSNotification.alloc().init()
        n.notify(title, subtitle, text)

else:
    # TODO: Add windows "action" center support, look @ https://github.com/Tzbob/python-windows-tiler/blob/master/pwt/notifyicon.py
    def notify(title, subtitle, text):
        print(title, ":", subtitle)
        print(text)

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
    parser.add_argument("-travel_min", type=int, default=40, help="Minimum number of minutes for route until notification")
    parser.add_argument("-origin", help="origin, ex: San Carlos/US-101 S/HOLLY ST")
    parser.add_argument("-dest", help="destination, ex: San Jose/CA-87 S/W CAPITOL EXPY")
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

    while True:
        paths = requests.get('http://services.my511.org/traffic/getpathlist.aspx', params=dest_obj)
        assert paths.status_code == 200
        paths = xmltodict.parse(paths.text)
        paths = paths["paths"]["path"]

        times = list(map(lambda x: int(x["currentTravelTime"]), paths))
        min_time = min(times)

        if min_time <= app_args.travel_min:
            text = "Current minimum travel time " + str(min_time) + " minutes" # + "" from: \n" + "/".join(app_args.origin) + " to: " + "/".join(app_args.dest)
            notify("511 time", "Target Travel Time Reached!", text)
            exit(0)

        time.sleep(app_args.period)

if __name__ == '__main__':
    main()
