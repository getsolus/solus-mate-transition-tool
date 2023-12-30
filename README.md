# Solus MATE Transition Tool

As of Solus 4.5 the MATE Desktop Environment is no longer being maintained. This is a tool is to help users transition to a Budgie or XFCE environment without completely reinstalling.

It uses packagekit under the hood and is extremely work in progress.

# TODO:
[] Create exhaustive list of XFCE pkgs to install (e.g. -c desktop.xfce and xfce4-desktop-branding)
[] Create exhaustive list of Budgie pkgs to install (e.g. -c desktop.budgie and budgie-desktop-branding)
[] Create exhaustive list of MATE pkgs to remove (e.g. -c desktop.mate and mate-desktop-branding)
[] Optional: read in pkg lists from a file
[] Override the default user-session to the chosen DE after install in lightdm seat until MATE is removed
[] More robust locking file
[] Handle window closures
[] Fix an annoying bug where the first element in the list isn't resolved by packagekit
[] Wait for packagekit async tasks (wrap around asyncio?)
[] Prompt reboot after installing
[] Packaging: setup meson
[] Packaging: Autostart for supported DE's (e.g. /usr/share/xdg/autostart/)
