; documentation seen at http://nsis.sourceforge.net/Docs/Chapter2.html
 
!define AppName "Inkscape Extension ThunderLaser"
!define AppVersion "v1.3"
!define ShortName "inkscape-thunderlaser"
!define Vendor "Fab Lab Region Nürnberg e.V."
!define Author "(C) 2017 Juergen Weigert <jw@fabmail.org>"
 

Name "${AppName} ${AppVersion}"
; The OutFile instruction is required and tells NSIS where to write the installer.
; you also need at least one section.
OutFile "../out/${ShortName}-${AppVersion}-setup.exe"

; On Windows x64, $PROGRAMFILES and $PROGRAMFILES32 point to C:\Program Files (x86) while $PROGRAMFILES64 points to C:\Program Files. 

; The temporary directory:  $TEMP

Section "${AppName}"
 ; OutPath according to http://www.inkscapeforum.com/viewtopic.php?t=4205
 SetOutPath "$PROGRAMFILES64\inkscape\share\extenstions"
 File "../../thunderlaser.py"
 File "../../thunderlaser.inx"
SectionEnd

