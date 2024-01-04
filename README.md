# Solus MATE Transition Tool

As of Solus 4.5 the MATE Desktop Environment is no longer being maintained. This is a tool is to help users transition to a Budgie or XFCE environment without completely reinstalling.

It uses packagekit under the hood and is extremely work in progress.

## TODO
- [x] Create exhaustive list of XFCE pkgs to install (e.g. -c desktop.xfce and xfce4-desktop-branding)
- [x] Create exhaustive list of Budgie pkgs to install (e.g. -c desktop.budgie and budgie-desktop-branding)
- [x] Create exhaustive list of MATE pkgs to remove (e.g. -c desktop.mate and mate-desktop-branding)
- [x] Optional: read in pkg lists from a file
- [x] Policykit integration (register on dbus and Policykit prompt, pkexec is not an option due to it dropping XDG_SESSION_DESKTOP)
- [x] Override the default user-session to the chosen DE after install in lightdm seat until MATE is removed
- [x] Async packagekit resolve
- [ ] More robust locking file
- [ ] Handle window closures
- [ ] Fix an annoying bug where the first element in the list isn't resolved by packagekit
- [x] Wait for packagekit async tasks (wrap around asyncio?)
- [x] Prompt reboot after installing
- [x] Notification prompt for existing MATE installs (take inspo from solus-update-checker)
- [x] Temporary autostart & autologin after new DE install
- [x] Packaging: setup meson
- [x] Uninstall ourselves after successful transition
- [ ] Optional: async dbus calls
- [ ] Optional: logfile: log packagekit actions and paths touched
- [ ] DBus: handle errors more gracefully
- [ ] Code cleanup: try and stop abusing callback data with hardcoded if statements
- [ ] Code cleanup: more robust error checking
- [ ] Code cleanup: handle application state more effectively
