@echo off
call settings.cmd
"Bat_To_Exe_Converter.exe" -bat "setup-weboob.bat" -save "setup-weboob-%WEBOOB_VERSION%-%ARCHITECTURE%.exe" -icon "ICON\weboobtxt.ico" -include "Bat_To_Exe_Converter.exe" -include "wget-%ARCHITECTURE%.exe" -include "weboob-%WEBOOB_VERSION%-py2.7.egg" -include "convertPNG2ICO.py" -include "ez_setup.py" -include "settings.cmd"