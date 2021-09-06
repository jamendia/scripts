#!/usr/bin/env bash
#
# A quick and dirty script to mount my phone and transfer files.
#
# Requirements: jmtpfs


if [[ $1 = "-m" ]]; then
   if [[ ! -d ~/phone ]]; then
       mkdir ~/phone
       echo "Phone successfully mounted to ~/phone"
   else
       echo "Phone successfully mounted to ~/phone"
   fi
   jmtpfs ~/phone
   exit 1
elif [[ $1 = "-u" ]]; then
    if fusermount -u ~/phone ; then
        rmdir ~/phone
        echo "Phone successfully unmounted"
        echo "Directory ~/phone was deleted"
    else
        echo "Could not unmount phone"
    fi
else
    printf "You have to select an option: -m to mount, -u to unmount.\n\n"
    printf "Remember also to set your phone on Transfer Files mode.\n"
    exit 1
fi
