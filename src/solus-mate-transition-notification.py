#!/usr/bin/env python3

import os
import subprocess
import sys
import time
import gettext

import gi.repository

gi.require_version('Gio', '2.0')
gi.require_version('Notify', '0.7')

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import Gio, GLib, GObject, Notify

UPDATE_NOTIF_TIMEOUT = 20000
UPDATE_DELTA_HOUR = 60 * 60
UPDATE_DELTA_FOURHOURLY = UPDATE_DELTA_HOUR * 4
PONG_FREQUENCY = 120

_ = gettext.gettext

class MateNotificationApp(Gio.Application):
    def __init__(self):
        Gio.Application.__init__(self,
                                 application_id="us.getsol.matetransition.notification",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        """Do we need to show the notification?"""
        if os.getlogin() == "live":
            sys.exit()

        self.connect("activate", self.on_activate)
        self.last_checked = time.time()

    def on_activate(self, app):
        Notify.init("MATE Notification nag")

        # Show notification on startup then on "pong" interval see if we need
        # to reshow.
        self.show_notification()
        GLib.timeout_add_seconds(PONG_FREQUENCY, self.do_reshow_notification)

        self.hold()

    def show_notification(self):
        """ Actually show the notification """
        self.store_update_time()
        self.notification = Notify.Notification.new(_("Solus Transition Service"), _("Solus MATE Edition is no longer supported. The MATE desktop environment will not be recieving new updates."), "software-update-urgent")
        self.notification.set_timeout(UPDATE_NOTIF_TIMEOUT)
        self.notification.add_action("open-matetransition-tool", _("Switch Solus Edition"),
                                     self.action_open_tool, None)
        self.notification.show()

    def action_open_tool(self, notification, action, user_data):
        """ Open the transition tool thingy """
        command = ["solus-mate-transition-tool"]
        try:
            subprocess.Popen(command)
        except Exception:
            pass
        notification.close()

    def store_update_time(self):
        """ Update timestamp """
        timestamp = time.time()
        self.last_checked = timestamp

    def do_reshow_notification(self):
        if self.is_reshow_notification_required():
            self.show_notification()
            return True
        # always return true so we keep the glib loop going
        return True

    def is_reshow_notification_required(self):
        """ Calculate timestamp interval on whether we need to renotify """
        delta = UPDATE_DELTA_FOURHOURLY
        next_time = self.last_checked + delta
        cur_time = time.time()
        print(next_time)
        print(cur_time)
        if next_time < cur_time:
            return True
        return False

if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)
    app = MateNotificationApp()
    app.run(sys.argv)
