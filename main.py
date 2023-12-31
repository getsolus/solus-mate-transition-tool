#!/usr/bin/python3

import gi
gi.require_version('PackageKitGlib', '1.0')
gi.require_version("Gtk", "3.0")

from gi.repository import GLib, PackageKitGlib, Gio, Gtk
import os
import sys

LOCKFILE="/var/tmp/solus-mate-transition-de"

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

        self.client = PackageKitGlib.Client()
        # FIXME: If you refresh repos then immediately try to resolve pkgs the first
        #        pkg will fail to resolve
        #self.pkit_update()

    def on_success_reboot_dialog(self, de: str, logo: str) -> None:
        dialog = Gtk.MessageDialog(
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Successfully Installed {de}",
        )
        dialog.format_secondary_text(
            "Reboot now to login to your new desktop environment. \n\n"
            "After logging in this program will auto-start to prompt you to remove MATE."
        )

        deimg = Gtk.Image()
        deimg.set_from_icon_name(logo, size = Gtk.IconSize.MENU)
        # FIXME. MessageDialog.set_image is deprecated
        dialog.set_image(deimg)

        dialog.show_all()
        dialog.run()
        # FIXME: Reboot on OK
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

    def pk_resolve_pkgs(self, pkgs, only_installed):
        """Resolve pkg name to package ids"""
        print("Pkit resolve")
        pk_package_ids = []

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

    def pkit_install_async(self, pkg_ids):
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
                            None  # callback data
                            )

    def pkit_remove_async(self, pkg_ids):
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
                            None  # callback data
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

        exists, content = self.read_lockfile()
        if exists == True:
           self.progress.set_text("Error: {} already installed".format(content))
           return

        btn = self.builder.get_object("install_budgie")
        btn.set_sensitive(False)

        if self.get_desktop_type() != "MATE":
            self.progress.set_text("Error: Not using MATE desktop environment")
            #return

        pkgs = self.resolve_budgie_pkgs()
        print(pkgs)

        if len(pkgs) == 0:
            self.progress.set_text("Error: resolved packages already installed")
        else:
            self.pkit_install_async(pkgs)
        # FIXME: How to wait for async packagekit result here

        self.write_lockfile("budgie")

    def install_xfce(self, button):

        exists, content = self.read_lockfile()
        print(exists, content)
        if exists == True:
           self.progress.set_text("Error: {} already installed".format(content))
           return

        btn = self.builder.get_object("install_xfce")
        self.builder.get_object("install_budgie").set_sensitive(False)
        btn.set_sensitive(False)

        if self.get_desktop_type() != "MATE":
            self.progress.set_text("Error: Not using MATE desktop environment")
            #return

        pkgs = self.resolve_xfce_pkgs()
        print(pkgs)

        if len(pkgs) == 0:
            self.progress.set_text("Error: resolved packages already installed")
        else:
            self.pkit_install_async(pkgs)
        # FIXME: How to wait for async packagekit result here

        self.write_lockfile("xfce")

    def remove_mate(self, button):
        # Read file in /var
        # Check XDG_DESKTOP_TYPE == desktop choice
        pkgs = self.resolve_mate_pkgs()
        print(pkgs)
        if len(pkgs) == 0:
            self.progress.set_text("Error: resolved packages already removed")
        else:
            self.pkit_remove_async(pkgs)

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
                contents = reader.readlines()
        return exists, contents

    def write_lockfile(self, de):
        with open(LOCKFILE, 'w') as writer:
            writer.write(de)
            print("wrote lock file")

App()
Gtk.main()



