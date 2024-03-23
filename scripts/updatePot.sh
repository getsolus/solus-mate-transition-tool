#!/bin/bash

function do_gettext()
{
    xgettext --package-name=solus-mate-transition-tool --package-version=0.3.1 $* --default-domain=solus-mate-transition-tool --join-existing --from-code=UTF-8 --no-wrap
}

function do_intltool()
{
    intltool-extract --type=$1 $2
}

rm solus-mate-transition-tool.po -f
touch solus-mate-transition-tool.po

# The .ui files
for file in `find src -name "*.ui"`; do
    if [[ `grep -F "translatable=\"yes\"" $file` ]]; then
        do_intltool gettext/glade $file
        do_gettext ${file}.h --add-comments --keyword=N_:1
        rm $file.h
    fi
done

# NOT .ui or ,build files, which should leave the python
for file in `find src -not  -name "*.ui" -or -name "*.build"`; do
        do_gettext $file --add-comments
done
mv solus-mate-transition-tool.po po/solus-mate-transition-tool.pot
#tx push -s
