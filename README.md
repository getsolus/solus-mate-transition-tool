# Solus MATE Transition Tool

As of Solus 4.5 the MATE Desktop Environment is no longer being maintained. This is a tool is to help users transition to a Budgie or XFCE environment without completely reinstalling.

It uses packagekit under the hood and is extremely work in progress.

## TODO
- [x] Create exhaustive list of XFCE pkgs to install (e.g. -c desktop.xfce and xfce4-desktop-branding)
- [x] Create exhaustive list of Budgie pkgs to install (e.g. -c desktop.budgie and budgie-desktop-branding)
- [x] Create exhaustive list of MATE pkgs to remove (e.g. -c desktop.mate and mate-desktop-branding)
- [x] Optional: read in pkg lists from a file
- [ ] Policykit integration (exec with pkexec or dbus obtainauth from freedesktop.policykit)
- [x] Override the default user-session to the chosen DE after install in lightdm seat until MATE is removed
- [ ] Async packagekit resolve
- [ ] More robust locking file
- [ ] Handle window closures
- [ ] Fix an annoying bug where the first element in the list isn't resolved by packagekit
- [x] Wait for packagekit async tasks (wrap around asyncio?)
- [x] Prompt reboot after installing
- [ ] Packaging: setup meson
- [ ] Packaging: Autostart for supported DE's (e.g. /usr/share/xdg/autostart/)
