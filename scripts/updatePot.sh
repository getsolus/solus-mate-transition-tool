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

# The python files
for file in `find src -name "*.py"` ; do
        do_gettext $file --add-comments
done

# Apparently, --from-code=UTF-8 is ignored if all your strings are ascii?
sed -i 's/charset=CHARSET/charset=UTF-8/g' solus-mate-transition-tool.po

mv solus-mate-transition-tool.po po/solus-mate-transition-tool.pot
#tx push -s
