
Edit: project resurrected.

I might improve and make this functional again.

Updated to use Python 3 and PyQt5. (No longer works with Python 2/Qt4.)

It used to reside here: https://code.google.com/archive/p/amphetype/
A random review: https://forum.colemak.com/topic/2201-training-with-amphetype/

TODO: rewrite this readme, rewrite help, restructure package;
everything below is from 12 years ago.

-----

Proper install is coming. I apologize for the current
mess. It was developed on a Windows machine with few
tools and no internet during a train ride and suffered
a few rewrites so the filenames aren't very descriptive
anymore.


To run, type:

python Amphetype.py


Depends on:

python-qt4  (that is, PyQt 4.3+)

OPTIONAL: py-editdist from http://www.mindrot.org/projects/py-editdist/
 - This latter dependancy is by no means critical and you will
 probably never get to use it. (For fetching words from a wordfile
 that are "similar" to your target words in the lesson generator.)
 If you don't have the module it will just select random words
 instead



