project(
    'solus-mate-transition-tool',
    ['c'],
    version: '0.3.1',
    license: [
        'GPL-2.0-only',
    ],
    default_options: [
        'prefix=/usr',
        'sysconfdir=/etc',
    ],
)

path_prefix = get_option('prefix')
path_datadir = join_paths(path_prefix, get_option('datadir'))
path_bindir = join_paths(path_prefix, get_option('bindir'))
path_libexecdir = join_paths(path_prefix, get_option('libexecdir'))

path_policydir = join_paths(path_datadir, 'polkit-1', 'actions')
path_dbussystemdir = join_paths(path_datadir, 'dbus-1', 'system.d')
path_dbussystemservicesdir = join_paths(path_datadir, 'dbus-1', 'system-services')

path_desktopdir = join_paths(path_datadir, 'applications')
path_autostartdesktopdir = join_paths(path_datadir, 'xdg', 'autostart')

localedir = join_paths(path_prefix, get_option('localedir'))
podir = join_paths(meson.source_root(), 'po')

path_generaldir = join_paths(path_datadir, 'solus-mate-transition-tool')

subdir('data')
subdir('pkgs')
subdir('po')
subdir('src')

report = [
    '    Build configuration:',
    '    ====================',
    '',
    '    prefix:                                 @0@'.format(path_prefix),
    '    datadir:                                @0@'.format(path_datadir),
    '    policykit dir:                          @0@'.format(path_policydir),
    '    dbus system dir:                        @0@'.format(path_dbussystemdir),
    '    dbus system services dir:               @0@'.format(path_dbussystemservicesdir),
    '    desktop dir:                            @0@'.format(path_desktopdir),
    '    autostart desktop dir:                  @0@'.format(path_autostartdesktopdir),
    '    localedir:                              @0@'.format(localedir),
    '    general dir:                            @0@'.format(path_generaldir),
]

# Output some stuff to validate the build config
message('\n\n\n' + '\n'.join(report) + '\n\n')
