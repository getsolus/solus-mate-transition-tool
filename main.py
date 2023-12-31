#!/usr/bin/python3

import gi
gi.require_version('PackageKitGlib', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gio, GLib, Gtk, PackageKitGlib
from configparser import ConfigParser
import os
import subprocess
import sys

LOCKFILE="/var/tmp/solus-mate-transition-de"

LIGHTDM_CONF_DIR = "/etc/lightdm/lightdm.conf.d/"
LIGHTDM_CONF_FILE = "1_solus-mate-transition-override.conf"

class App():
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("solus-mate-transition.ui")
        self.window = self.builder.get_object("us.getsol.matetransition")
        self.window.connect("delete-event", Gtk.main_quit)
        self.progress = self.builder.get_object("progress")
        self.window.show()

        self.pkit_cancellable = None

        self.builder.get_object("install_budgie").connect("clicked", self.install_budgie)
        self.builder.get_object("install_xfce").connect("clicked", self.install_xfce)
        self.builder.get_object("remove_mate").connect("clicked", self.remove_mate)

        exists, content = self.read_lockfile()

        # No lockfile exists so we wan't to be using the MATE session
        if exists == False and self.get_desktop_type() != "mate":
            self.builder.get_object("install_budgie").set_sensitive(False)
            self.builder.get_object("install_budgie").set_tooltip_text("")
            self.builder.get_object("install_xfce").set_sensitive(False)
            self.builder.get_object("install_xfce").set_tooltip_text("")
            self.on_error_dialog("Error", "Logout and login to the MATE session first to continue")

        # Lockfile exists so ensure the current DE session matches the lockfile
        if exists == True and content is not None:
            # FIXME: Maybe resolve packages again here to confirm all is installed
            self.builder.get_object("install_budgie").set_sensitive(False)
            self.builder.get_object("install_budgie").set_tooltip_text("")
            self.builder.get_object("install_xfce").set_sensitive(False)
            self.builder.get_object("install_xfce").set_tooltip_text("")
            if self.get_desktop_type() == content:
                self.builder.get_object("remove_mate").set_sensitive(True)
                self.builder.get_object("remove_mate").set_tooltip_text("Uninstall MATE to complete transition")
            else:
                self.on_error_dialog("Error",
                                     f"{content} is installed but you are not logged into that desktop environment.\nLogout and login to the {content} session to continue.")

        self.client = PackageKitGlib.Client()
        # FIXME: If you refresh repos then immediately try to resolve pkgs the first
        #        pkg will fail to resolve
        #self.pkit_update()

    def on_success_reboot_dialog(self, de: str, logo: str) -> None:
        dialog = Gtk.MessageDialog(
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK,
            text=f"Successfully Installed {de}",
        )
        reboot_btn = dialog.add_button("Reboot", Gtk.ResponseType.ACCEPT)
        # TODO: Set reboot color to a nice red
        #reboot_btn.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("red"))
        # set image to object-rotate-right
        dialog.format_secondary_text(
            "Reboot now to login to your new desktop environment automatically. \n\n"
            "This program will then auto-start to prompt you to remove MATE."
        )

        deimg = Gtk.Image()
        deimg.set_from_icon_name(logo, size = Gtk.IconSize.MENU)
        # FIXME. MessageDialog.set_image is deprecated
        dialog.set_image(deimg)

        dialog.show_all()
        res = dialog.run()
        if res == Gtk.ResponseType.ACCEPT:
            # FIXME: some sort of nice desktop api to use here?
            subprocess.run(["systemctl", "reboot"])
        dialog.destroy()

    def on_error_dialog(self, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CANCEL,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def finished(self):
        self.progress.set_fraction(100.0)
        self.progress.set_text("Finished")

    def on_pkit_progress(self, progress, ptype, data=None):
        if progress.get_status() == PackageKitGlib.StatusEnum.DOWNLOAD:
            self.progress.set_text("Downloading...")
        elif progress.get_status() == PackageKitGlib.StatusEnum.INSTALL:
            self.progress.set_text("Installing...")
        elif progress.get_status() == PackageKitGlib.StatusEnum.REMOVE:
            self.progress.set_text("Removing...")
        elif progress.get_status() == PackageKitGlib.StatusEnum.CANCEL:
            self.progress.set_text("Cancelling...")
        elif progress.get_status() == PackageKitGlib.StatusEnum.LOADING_CACHE:
            self.progress.set_text("Loading cache...")
        else:
            self.progress.set_text("")
        if ptype == PackageKitGlib.ProgressType.PERCENTAGE:
            prog_value = progress.get_property('percentage')
            self.progress.set_fraction(prog_value / 100.0)

    def on_refresh_finished(self, source, result, data=None):
        print("Pkit refreshed cache")
        self.progress.set_text("Cache updated")

    def on_pkit_finished(self, source, result, data=None):
        self.finished()
        print("Pkit update finished")
        try:
            results = source.generic_finish(result)
        except Exception as e:
            error = e.message
            self.progress.set_text("Error: {}".format(error))
            print("Pkit update error:", e.message)

        # FIXME: callback data/ref. Clean this shit up
        if data == "xfce":
            self.write_lockfile("XFCE")
            self.write_lightdm_autologin_conf("xfce")
            self.on_success_reboot_dialog(de="XFCE", logo="xfce4-logo")
        if data == "budgie":
            self.write_lockfile("Budgie")
            self.write_lightdm_autologin_conf("budgie")
            self.on_success_reboot_dialog(de="Budgie", logo="budgie-start-here-symbolic")
        if data == "mate":
            self.remove_lockfile()
            self.remove_lightdm_conf()

    def pk_resolve_pkgs(self, pkgs, only_installed):
        """Resolve pkg name to package ids"""
        print("Pkit resolve")
        pk_package_ids = []

        # FIXME: Resolve all the packages in one call with a formatted string instead of looping
        #        Then filter out installed/not_installed. Will be quicker.
        # FIXME: Use resolve_async if possible.
        for name in pkgs:
            print(name)
            try:
                res = self.client.resolve(PackageKitGlib.FilterEnum.NONE, (name,), None, self.on_pkit_progress, None)
                package_ids = res.get_package_array()
                name = package_ids[0].get_id()
                is_installed = package_ids[0].get_info() & PackageKitGlib.InfoEnum.INSTALLED == 1
                if only_installed == False and is_installed == True:
                    print("Skipping {}".format(name))
                elif only_installed == True and is_installed == False:
                    print("Skipping {}".format(name))
                else:
                    pk_package_ids.append(name)

            except Exception as e:
                error = e.message
                self.progress.set_text("Error: {}".format(error))
                print("Pkit update error:", e.message)
        return pk_package_ids

    def pkit_update(self):
        """Refresh packagekit repos"""
        print("Pkit update")
        self.pkit_cancellable = Gio.Cancellable()
        self.client.refresh_cache_async(True, self.pkit_cancellable, self.on_pkit_progress, (None, ), self.on_refresh_finished, (None, ))

    def pkit_install_async(self, pkg_ids: list, ref: str) -> None:
        """Install packages with resolved pkg ids asynchronously"""
        print("Pkit install")
        self.pkit_cancellable = Gio.Cancellable()
        task = PackageKitGlib.Task()
        print(pkg_ids)
        if len(pkg_ids) > 0:
            print(pkg_ids)
            self.client.install_packages_async(False, # trusted only
                            pkg_ids,
                            self.pkit_cancellable,  # cancellable
                            self.on_pkit_progress,
                            (None, ),  # progress data
                            self.on_pkit_finished,  # callback ready
                            ref  # callback data
                            )

    def pkit_remove_async(self, pkg_ids: list, ref: str) -> None:
        """Remove packages with resolved pkg ids asynchronously"""
        print("Pkit remove")
        self.pkit_cancellable = Gio.Cancellable()
        task = PackageKitGlib.Task()
        if len(pkg_ids) > 0:
            print(pkg_ids)
            self.client.remove_packages_async(pkg_ids,
                            False,  # allow deps
                            True,  # autoremove
                            self.pkit_cancellable,  # cancellable
                            self.on_pkit_progress,
                            (None, ),  # progress data
                            self.on_pkit_finished,  # callback ready
                            ref  # callback data
                            )

    def pkit_cancel(self, button):
        """Cancel packagekit operation if supported"""
        print("Pkit cancel")
        if self.pkit_cancellable != None:
            self.pkit_cancellable.cancel()

    def get_desktop_type(self):
        desktop = os.environ['XDG_SESSION_DESKTOP']
        print(desktop)
        return desktop

    def install_budgie(self, button):
        btn = self.builder.get_object("install_budgie")
        btn.set_sensitive(False)

        pkgs = self.resolve_budgie_pkgs()
        print(pkgs)

        if len(pkgs) == 0:
            self.progress.set_text("Error: resolved packages already installed")
        else:
            self.pkit_install_async(pkgs, ref="budgie")

    def install_xfce(self, button):
        btn = self.builder.get_object("install_xfce")
        self.builder.get_object("install_budgie").set_sensitive(False)
        btn.set_sensitive(False)

        pkgs = self.resolve_xfce_pkgs()
        print(pkgs)

        if len(pkgs) == 0:
            self.progress.set_text("Error: resolved packages already installed")
        else:
            self.pkit_install_async(pkgs, ref="xfce")

    def remove_mate(self, button):
        pkgs = self.resolve_mate_pkgs()
        print(pkgs)
        if len(pkgs) == 0:
            self.progress.set_text("Error: resolved packages already removed")
        else:
            self.pkit_remove_async(pkgs, ref="mate")

    def read_pkgs_file(self, de) -> list:
        path = "{}-pkgs.txt".format(de)
        contents = []

        # FIXME: Handle reading from installed location e.g. /usr
        try:
            with open(path, "r") as reader:
                contents = reader.read().splitlines()
            print(contents)
        except Exception as e:
            self.progress.set_text("Error: {}".format(error))
            print("Error Failed to read {}, error:", path, e.message)

        if len(contents) == 0:
            self.progress.set_text("Error: no packages found in {}".format(path))
            print("Error: No packages found in {}", path)

        return contents

    def resolve_budgie_pkgs(self):
        pkgs = self.read_pkgs_file("budgie")
        return self.pk_resolve_pkgs(pkgs, False)

    def resolve_xfce_pkgs(self):
        pkgs = self.read_pkgs_file("xfce")
        return self.pk_resolve_pkgs(pkgs, False)

    def resolve_mate_pkgs(self):
        pkgs = self.read_pkgs_file("mate")
        return self.pk_resolve_pkgs(pkgs, True)

    def read_lockfile(self):
        exists = False
        contents = ""
        if os.path.exists(LOCKFILE):
            exists = True
            with open(LOCKFILE, "r") as reader:
                contents = reader.read()
        return exists, contents

    def write_lockfile(self, de):
        with open(LOCKFILE, 'w') as writer:
            writer.write(de)
            print("wrote lock file")

    def remove_lockfile(self) -> None:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
            print("Removed {}".format(LOCKFILE))

    # FIXME: polkit shit
    def write_lightdm_autologin_conf(self, session: str) -> None:
        if os.path.exists("/etc/lightdm/lightdm.conf"):
            print("Warning: user-set /etc/lightdm/lightdm.conf exists, our temporary override may not function")

        if session != "mate" or session != "xfce":
            print("Warning: untested session type {}".format(session))

        conf_path = os.path.join(LIGHTDM_CONF_DIR, LIGHTDM_CONF_FILE)

        os.makedirs(os.path.dirname(LIGHTDM_CONF_DIR), exist_ok=True)
        config = ConfigParser()
        config.read(conf_path)
        config.add_section("Seat:*")
        config.set('Seat:*', 'autologin-session', session)
        config.set('Seat:*', "autologin-user", os.getlogin())

        with open(conf_path, 'w') as f:
            config.write(f)

    # FIXME: polkit shit
    def remove_lightdm_conf(self) -> None:
        conf_path = os.path.join(LIGHTDM_CONF_DIR, LIGHTDM_CONF_FILE)
        if os.path.exists(conf_path):
            os.remove(conf_path)
            print("Removed lightdm override: {}".format(path))

App()
Gtk.main()



