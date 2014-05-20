@echo off
call settings.cmd
"Bat_To_Exe_Converter_%LOCAL_ARCHITECTURE%.exe" -bat "setup-weboob.bat" -save "setup-weboob-%WEBOOB_VERSION%-%ARCHITECTURE%.exe" -icon "ICON\weboobtxt.ico" -include "Bat_To_Exe_Converter_%ARCHITECTURE%.exe" -include "wget-%ARCHITECTURE%.exe" -include "%WEBOOB%" -include "convertPNG2ICO.py" -include "ez_setup.py" -include "settings.cmd"
