@echo off
call settings.cmd
"Bat_To_Exe_Converter.exe" -bat "setup-weboob.bat" -save "setup-weboob-%WEBOOB_VERSION%.exe" -icon "ICON\weboobtxt.ico" -include "Bat_To_Exe_Converter.exe" -include "wget-1.11.4-1-setup.exe" -include "weboob-%WEBOOB_VERSION%-py2.7.egg" -include "convertPNG2ICO.py" -include "ez_setup.py" -include "settings.cmd"
