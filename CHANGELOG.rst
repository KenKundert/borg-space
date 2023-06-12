Releases
========

Latest development release
--------------------------
| Version: 2.1
| Released: 2023-06-09


2.2.0 (2023-06-11)
------------------

- Improves the formatting of the X and Y axis labels in graphs.
- Allows host names to begin with a digit.
- Improves the consistency of the error handling.


2.1.0 (2023-06-09)
------------------

This version fixes a number of issues with the prior version.  In addition there 
are changes that are not backward compatible:

- The *repositories* setting is now limited to being a dictionary.
- The *normal* style has been renamed *table*.
- The files in ~/.local/share/borg-space all use the full spec as the base of 
  their name.  Any files that do not follow this convention must be renamed, 
  otherwise they will be ignored.  For example, if you currently have *home.nt* 
  in this directory, then you should rename it to 
  *home@❬your_hostname❭~❬your_username❭*.
- The *repo* field has been replaced by *name*, *spec*, and *full_spec*.


2.0.0 (2023-05-15)
------------------

Version 2 of *Borg-Space* is a big change from earlier versions and is not 
backward compatible.  With version 1 and earlier *Borg-Space* would read 
*Emborg* configuration files to find the information it needed to call *Borg* 
directly to determine the current amount of space required by a repository.  
This results in *Borg* creating a local cache for the repository which could be 
huge.  This version of *Borg-Space* exploits a new feature of *Emborg v1.36*, 
which routinely records the space consumed by the repository.  This information 
is available in ~/.local/share/emborg/❬config❭.latest.nt.  *Borg-Space* simply 
reads this file, which saves considerable time and requires no additional disk 
space.

*Borg-Space 2* can access remote repositories, but user running *Borg-Space* 
must have SSH access to the hosts being backed up, and the *Emborg* .latest.nt 
files must be accessible.


1.0.0 (2023-04-08)
------------------
- Improve plotting.


0.4.0 (2022-10-22)
------------------
- Tweak graph axes labels.


0.3.0 (2022-03-21)
------------------
- Upgrade required to support *Emborg* version 1.31.


0.2.0 (2021-10-01)
------------------
- Fixed incompatibility with *Emborg* version 1.26.


0.1.0 (2021-09-30)
------------------
- Added ability to save graph as SVG file.


0.0.0 (2021-09-25)
------------------
- Initial release
