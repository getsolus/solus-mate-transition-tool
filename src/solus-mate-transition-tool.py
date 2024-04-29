#!/usr/bin/env python3

from configparser import ConfigParser
import gettext
import locale
import os
import subprocess
import sys

import gi
gi.require_version('Gdk', '3.0')
gi.require_version("Gtk", "3.0")
gi.require_version('PackageKitGlib', '1.0')

from gi.repository import Gdk, Gio, GLib, Gtk, PackageKitGlib
import dbus

LOCKFILE="/var/tmp/solus-mate-transition-de"

DESKTOP_AUTOSTART_DIR = "/etc/xdg/autostart"
DESKTOP_AUTOSTART_FILE = "us.getsol.matetransition.desktop"

LIGHTDM_CONF_DIR = "/etc/lightdm/lightdm.conf.d/"
LIGHTDM_CONF_FILE = "1_solus-mate-transition-override.conf"

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

APP = 'solus-mate-transition-tool'
LOCALE_DIR = "/usr/share/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

class App():

    AUTHORIZER_NAME = 'us.getsol.matetransition.Authorizer'
    AUTHORIZER_PATH = '/us/getsol/matetransition/Authorizer'
    AUTHORIZER_IFACE = 'us.getsol.matetransition.Authorizer'

    def __init__(self):

        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(APP)
        if os.path.exists(os.path.join(CURRENT_DIR, "solus-mate-transition.ui")):
            ui_filename = os.path.join(CURRENT_DIR, "solus-mate-transition.ui")
        else:
            ui_filename = "/usr/share/solus-mate-transition-tool/solus-mate-transition.ui"

        self.builder.add_from_file(ui_filename)
        self.window = self.builder.get_object("us.getsol.matetransition")
        self.window.connect("delete-event", Gtk.main_quit)
        self.progress = self.builder.get_object("progress")
        self.window.show()

        self.pkit_cancellable = None

        self.builder.get_object("install_budgie").connect("clicked", self.install_budgie)
        self.builder.get_object("install_xfce").connect("clicked", self.install_xfce)
        self.builder.get_object("remove_mate").connect("clicked", self.remove_mate)

        # DE strings for Budgie
        self.budgie_id = "budgie"
        self.budgie_pretty_name = "Budgie"
        self.budgie_desktop_session = "budgie-desktop"
        self.budgie_logo = "budgie-start-here-symbolic"

        # DE strings for MATE
        self.mate_id = "mate"
        self.mate_pretty_name = "MATE"
        self.mate_desktop_session = "mate"

        # DE strings for XFCE
        self.xfce_id = "xfce"
        self.xfce_pretty_name = "XFCE"
        self.xfce_desktop_session = "xfce"
        self.xfce_logo = "xfce4-logo"

        self.startup_checks()

        self.client = PackageKitGlib.Client()
        self.pkit_update()

        # init dbus conn to our authorizer service
        try:
            self.obj = dbus.SystemBus().get_object(self.AUTHORIZER_NAME,
                    self.AUTHORIZER_PATH)
            self.iface = dbus.Interface(self.obj, self.AUTHORIZER_IFACE)
        except dbus.exceptions.DBusException as e:
            print(f"Could not connect to {self.AUTHORIZER_NAME}")
            sys.stderr.write(str(e))
            sys.exit(1)

    def state_enable_remove(self) -> None:
        self.builder.get_object("remove_mate").set_sensitive(True)
        self.builder.get_object("remove_mate").set_tooltip_text(_("Uninstall MATE to complete transition"))

    def state_disable_install(self) -> None:
        self.builder.get_object("install_budgie").set_sensitive(False)
        self.builder.get_object("install_budgie").set_tooltip_text("")
        self.builder.get_object("install_xfce").set_sensitive(False)
        self.builder.get_object("install_xfce").set_tooltip_text("")

    def startup_checks(self) -> None:
        exists, de, pretty_name, desktop_session = self.read_lockfile()

        # No lockfile exists so we want to be using the MATE session
        if exists == False and self.get_desktop_type() != self.mate_desktop_session:
            self.state_disable_install()
            self.on_error_dialog(_("Error"),
                                 _("Logout and login to the MATE session first to continue"))

        # Lockfile exists so ensure the current DE session matches the lockfile
        if exists is True and de is not None:
            # FIXME: Maybe resolve packages again here to confirm all is installed
            self.state_disable_install()
            if self.get_desktop_type().casefold() == desktop_session.casefold():
                self.state_enable_remove()
            else:
                self.on_error_dialog(_("Error"),
                                     _("{} is installed but you are not logged into that desktop environment.\nLogout and login to the {} session to continue.").format(pretty_name,pretty_name))


    def on_success_reboot_dialog(self, de: str, logo: str) -> None:
        dialog = Gtk.MessageDialog(
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK,
            text=_("Successfully Installed {}").format(de),
        )
        reboot_btn = dialog.add_button(_("Reboot"), Gtk.ResponseType.ACCEPT)
        # TODO: Set reboot color to a nice red
        #reboot_btn.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("red"))
        # set image to object-rotate-right
        dialog.format_secondary_text(_(
            "Reboot now to login to your new desktop environment automatically. \n\n"
            "This program will then auto-start to prompt you to remove MATE."
        ))

        deimg = Gtk.Image()
        deimg.set_from_icon_name(logo, size = Gtk.IconSize.DIALOG)
        # FIXME. MessageDialog.set_image is deprecated
        dialog.set_image(deimg)

        dialog.show_all()
        res = dialog.run()
        if res == Gtk.ResponseType.ACCEPT:
            # FIXME: some sort of nice desktop api to use here?
            subprocess.run(["systemctl", "reboot"], check=True)
        dialog.destroy()

    def on_success_complete_dialog(self, de: str) -> None:
        dialog = Gtk.MessageDialog(
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.CLOSE,
            text=_("Successfully Completed Transition to {}").format(de),
        )
        dialog.format_secondary_text(_(
            "We hope you enjoy using your new desktop environment."
        ))

        deimg = Gtk.Image()
        deimg.set_from_icon_name("distributor-logo-solus", size = Gtk.IconSize.DIALOG)
        # FIXME. MessageDialog.set_image is deprecated
        dialog.set_image(deimg)

        dialog.show_all()
        res = dialog.run()
        if res == Gtk.ResponseType.CLOSE:
            self.window.close()
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
        self.progress.set_text(_("Finished"))

    def write_temporary_config_files(self, ref: str) -> None:
        try:
            result = self.iface.write_desktop_autostart_conf()
            result = self.iface.write_lightdm_autologin_conf(ref, os.getlogin())
            print(result)
        except dbus.exceptions.DBusException as e:
            # dbus-python exception handling is problematic.
            if 'Authorization failed' in str(e):
                # The user knows this already; don't show a FatalErrorWindow.
                sys.exit(1)
            else:
                self.on_error_dialog(_("Failed to write temporary config file"), e)

    def remove_temporary_config_files(self) -> None:
        try:
            result = self.iface.remove_desktop_autostart_conf()
            print(result)
            result = self.iface.remove_lightdm_conf()
            print(result)
        except dbus.exceptions.DBusException as e:
            # dbus-python exception handling is problematic.
            if 'Authorization failed' in str(e):
                # The user knows this already; don't show a FatalErrorWindow.
                sys.exit(1)
            else:
                self.on_error_dialog(_("Failed to remove temporary config file"), e)

    def on_pkit_progress(self, progress, ptype, data=None):
        if progress.get_status() == PackageKitGlib.StatusEnum.DOWNLOAD:
            self.progress.set_text(_("Downloading..."))
        elif progress.get_status() == PackageKitGlib.StatusEnum.INSTALL:
            self.progress.set_text(_("Installing..."))
        elif progress.get_status() == PackageKitGlib.StatusEnum.REMOVE:
            self.progress.set_text(_("Removing..."))
        elif progress.get_status() == PackageKitGlib.StatusEnum.CANCEL:
            self.progress.set_text(_("Cancelling..."))
        elif progress.get_status() == PackageKitGlib.StatusEnum.LOADING_CACHE:
            self.progress.set_text(_("Loading cache..."))
        else:
            self.progress.set_text("")
        if ptype == PackageKitGlib.ProgressType.PERCENTAGE:
            prog_value = progress.get_property('percentage')
            self.progress.set_fraction(prog_value / 100.0)

    def on_refresh_finished(self, source, result, data=None):
        print(_("Packagekit refreshed cache"))
        self.progress.set_text(_("Cache updated"))

    def on_pkit_finished(self, source, result, data=None):
        self.finished()
        # FIXME: why does this happen with only this string??
        # UnboundLocalError: cannot access local variable '_' where it is not associated with a value
        #print(_("Packagekit update finished"))
        try:
            results = source.generic_finish(result)
        except Exception as e:
            self.progress.set_text(_("Error: {}").format(e))
            print(_("Packagekit update error:"), e)
            # Reset button states on err
            # FIXME, handle state more generically!
            if data == self.mate_id:
                self.builder.get_object("remove_mate").set_sensitive(True)
            else:
                self.builder.get_object("install_xfce").set_sensitive(True)
                self.builder.get_object("install_budgie").set_sensitive(True)
            #return

        # FIXME: callback data/ref. Clean this shit up
        if data == self.xfce_id:
            self._write_lockfile(de=self.xfce_id, pretty_name=self.xfce_pretty_name, desktop_session=self.xfce_desktop_session)
            self.write_temporary_config_files(ref=self.xfce_desktop_session)
            self.on_success_reboot_dialog(de=self.xfce_id, logo=self.xfce_logo)
        if data == self.budgie_id:
            self._write_lockfile(de=self.budgie_id, pretty_name=self.budgie_pretty_name, desktop_session=self.budgie_desktop_session)
            self.write_temporary_config_files(ref=self.budgie_desktop_session)
            self.on_success_reboot_dialog(de=self.budgie_pretty_name, logo=self.budgie_logo)
        if data == self.mate_id:
            _, _, pretty_name, _ = self.read_lockfile()
            self._remove_lockfile()
            self.remove_temporary_config_files()
            self._remove_transition_tool()
            self.on_success_complete_dialog(de=pretty_name)

    def pk_resolve_pkgs_async(self, pkgs: list, only_installed: bool, ref: str) -> None:
        print(_("Packagekit resolve"))

        def on_resolve_async(source, result, data=None) -> bool:
            results = source.generic_finish(result)
            package_ids = results.get_package_array()

            if len(package_ids) == 0:
                return False

            pkgs = []
            for i in package_ids:
                name = i.get_id()
                is_installed = i.get_info() & PackageKitGlib.InfoEnum.INSTALLED == 1
                not_installed = i.get_info() & PackageKitGlib.InfoEnum.INSTALLED == 0
                print(_("is installed"), is_installed, name)
                # FIXME: make this not shit
                if data == self.mate_id and not_installed is True:
                    print(_("Skipping {}").format(name))
                elif data == self.xfce_id and is_installed is True:
                    print(_("Skipping {}").format(name))
                elif data == self.budgie_id and is_installed is True:
                    print(_("Skipping {}").format(name))
                else:
                    pkgs.append(name)

            # FIXME: Make this not shit
            if data == self.xfce_id:
                self.pkit_install_async(pkgs, ref=data)
            if data == self.budgie_id:
                self.pkit_install_async(pkgs, ref=data)
            if data == self.mate_id:
                self.pkit_remove_async(pkgs, ref=data)
            return True

        self.client.resolve_async(False, # transaction flags (filters, etc.)
                                    pkgs,
                                    self.pkit_cancellable,  # cancellable
                                    self.on_pkit_progress,
                                    (None, ),  # progress data
                                    on_resolve_async,  # callback ready
                                    ref  # callback data
                                    )

    def pkit_update(self):
        """Refresh packagekit repos"""
        print(_("Packagekit update"))
        self.pkit_cancellable = Gio.Cancellable()
        self.client.refresh_cache_async(True, # transaction flags (filters, etc.)
                                        self.pkit_cancellable, # cancellable
                                        self.on_pkit_progress,
                                        (None, ), # progress data
                                        self.on_refresh_finished, # callback ready
                                        (None, ) # callback data
                                        )

    def pkit_install_async(self, pkg_ids: list, ref: str) -> None:
        """Install packages with resolved pkg ids asynchronously"""
        print(_("Packagekit install"))
        self.pkit_cancellable = Gio.Cancellable()
        print(pkg_ids)
        if len(pkg_ids) > 0:
            print(pkg_ids)
            self.client.install_packages_async(False, # transaction flags (filters, etc.)
                            pkg_ids,
                            self.pkit_cancellable,  # cancellable
                            self.on_pkit_progress,
                            (None, ),  # progress data
                            self.on_pkit_finished,  # callback ready
                            ref  # callback data
                            )

    def pkit_remove_async(self, pkg_ids: list, ref: str) -> None:
        """Remove packages with resolved pkg ids asynchronously"""
        print(_("Packagekit remove"))
        self.pkit_cancellable = Gio.Cancellable()
        if len(pkg_ids) > 0:
            print(pkg_ids)
            self.client.remove_packages_async(False, # trusted only
                            pkg_ids,
                            False, # allow deps
                            False, # autoremove
                            self.pkit_cancellable, # cancellable
                            self.on_pkit_progress,
                            (None, ),  # progress data
                            self.on_pkit_finished,  # callback ready
                            ref  # callback data
                            )

    def pkit_cancel(self, button) -> None:
        """Cancel packagekit operation if supported"""
        print(_("Packagekit cancel"))
        if self.pkit_cancellable is not None:
            self.pkit_cancellable.cancel()

    def get_desktop_type(self) -> str:
        desktop = os.environ.get("XDG_SESSION_DESKTOP")
        print(desktop)
        if desktop is None:
            print(_("Warning: XDG_SESSION_DESKTOP is unset!"))
            return ""
        return desktop

    def install_budgie(self, button) -> None:
        self.builder.get_object("install_budgie").set_sensitive(False)
        self.builder.get_object("install_xfce").set_sensitive(False)

        self.resolve_budgie_pkgs(ref=self.budgie_id)

    def install_xfce(self, button) -> None:
        self.builder.get_object("install_xfce").set_sensitive(False)
        self.builder.get_object("install_budgie").set_sensitive(False)

        self.resolve_xfce_pkgs(ref=self.xfce_id)

    def remove_mate(self, button) -> None:
        self.builder.get_object("remove_mate").set_sensitive(False)

        self.resolve_mate_pkgs(ref=self.mate_id)

    def read_pkgs_file(self, de: str) -> list:
        pkgs_file = "{}-pkgs.txt".format(de)

        if os.path.exists(os.path.join("../", pkgs_file)):
            path = pkgs_file
        else:
            path = os.path.join("/usr/share/solus-mate-transition-tool/", pkgs_file)
        contents = []

        # FIXME: Handle reading from installed location e.g. /usr
        try:
            with open(path, "r") as reader:
                contents = reader.read().splitlines()
            print(contents)
        except IOError as e:
            self.progress.set_text("Error: {}".format(e))
            print(_("Error Failed to read {}, error:"), path, e)

        if len(contents) == 0:
            self.progress.set_text("Error: no packages found in {}".format(path))
            print(_("Error: No packages found in {}"), path)

        return contents

    def resolve_budgie_pkgs(self, ref: str) -> None:
        pkgs = self.read_pkgs_file(self.budgie_id)
        print(pkgs)
        self.pk_resolve_pkgs_async(pkgs, False, ref)

    def resolve_xfce_pkgs(self, ref: str) -> None:
        pkgs = self.read_pkgs_file(self.xfce_id)
        print(pkgs)
        self.pk_resolve_pkgs_async(pkgs, False, ref)

    def resolve_mate_pkgs(self, ref: str) -> None:
        pkgs = self.read_pkgs_file(self.mate_id)
        print(pkgs)
        self.pk_resolve_pkgs_async(pkgs, True, ref)

    def read_lockfile(self) -> tuple[bool, str, str, str]:
        exists = False

        if not os.path.exists(LOCKFILE):
            return exists, None, None, None
        else:
            exists = True
            config = ConfigParser()
            config.read(LOCKFILE)
            de = config.get("main", "de")
            pretty_name = config.get("main", "pretty_name")
            desktop_session = config.get("main", "desktop_session")
            return exists, de, pretty_name, desktop_session

    def _write_lockfile(self, de: str, pretty_name: str, desktop_session: str) -> None:
        if de is None:
            raise IntersectException("de must not be empty")
        if pretty_name is None:
            raise IntersectException("pretty_name must not be empty")
        if desktop_session is None:
            raise IntersectException("desktop_session must not be empty")

        config = ConfigParser()
        config.add_section("main")
        config.set("main", "de", de)
        config.set("main", "pretty_name", pretty_name)
        config.set("main", "desktop_session", desktop_session)

        with open(LOCKFILE, 'w') as writer:
                config.write(writer)
                print(f"Successfully wrote {LOCKFILE}")

    def _remove_lockfile(self) -> None:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
            print(_("Removed {}").format(LOCKFILE))

    def _remove_transition_tool(self) -> None:
        """ Uninstall ourselves after successfully completing """
        pkg = "solus-mate-transition-tool"

        def on_resolved(source, result, data=None):
            """ Inner function callback from resolve_async """
            results = source.generic_finish(result)
            package_ids = results.get_package_array()

            if len(package_ids) == 0:
                return

            pkgs = []
            for i in package_ids:
                pkgs.append(i.get_id())

            if len(package_ids) > 0:
                self.pkit_remove_async(pkgs, None)
            else:
                self.progress.set_text(_("Error: Couldn't resolve ourself with packagekit"))

        self.pkit_cancellable = Gio.Cancellable()
        self.client.resolve_async(PackageKitGlib.FilterEnum.from_string("INSTALLED"), # filters
                            [pkg],
                            self.pkit_cancellable,  # cancellable
                            self.on_pkit_progress,
                            (None, ),  # progress data
                            on_resolved,  # callback ready
                            None  # callback data
                            )

App()
Gtk.main()
