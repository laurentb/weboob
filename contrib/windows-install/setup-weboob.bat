@echo off
setlocal enableextensions enabledelayedexpansion

call settings.cmd

echo.
echo 0.Set proxy
set/P HTTP_PROXY=Enter HTTP_PROXY if needed : 
set/P HTTPS_PROXY=Enter HTTPS_PROXY if needed :

echo.
echo 1.GNU/WGET Init

set WGET=wget-%ARCHITECTURE%.exe

echo.
echo 2.Check Python 2.7 Installation

set KEY_NAME=HKLM\Software\Python\PythonCore\2.7\InstallPath
if %ARCHITECTURE% == x64 (
	set KEY_NAME=HKLM\SOFTWARE\Python\PythonCore\2.7\InstallPath
)

REG QUERY !KEY_NAME! > nul || 	(
									set PYTHON_MSI=python-2.7.5.msi
									if %ARCHITECTURE% == x64 (
										set PYTHON_MSI=python-2.7.5.amd64.msi			
									)
									
									echo 2.1 Download !PYTHON_MSI!
									"%WGET%" -o python_donwload --no-check-certificate "http://www.python.org/ftp/python/2.7.5/!PYTHON_MSI!"
									
									echo 2.2 Setup !PYTHON_MSI!
									!PYTHON_MSI!
									
									del !PYTHON_MSI!
									del python_donwload
								)
								
for /F "tokens=4" %%A IN ('REG QUERY !KEY_NAME!') do (
    set PythonPath=%%A
)

echo.
echo 3.Check PyQt4 Installation
set KEY_NAME=HKLM\Software\PyQt4\Py2.7\InstallPath
REG QUERY %KEY_NAME% > nul || 	(

	echo 3.1 Download PyQt4
	"%WGET%" -o qt_download http://heanet.dl.sourceforge.net/project/pyqt/PyQt4/PyQt-4.10.3/PyQt4-4.10.3-gpl-Py2.7-Qt4.8.5-%ARCHITECTURE%.exe

	echo 3.2 Setup PyQt4
	PyQt4-4.10.3-gpl-Py2.7-Qt4.8.5-%ARCHITECTURE%.exe

	del PyQt4-4.10.3-gpl-Py2.7-Qt4.8.5-%ARCHITECTURE%.exe
	del qt_download
)

echo.
echo 4.Check EasyInstall
if exist "%PythonPath%Scripts\easy_install.exe" (
	goto :InstallWeboobDependances
) else (

	echo 4.1 Setup setuptools	
	%PythonPath%python.exe ez_setup.py || goto :InstallFailed
	
	del setuptools-1.1.6.tar.gz
	
	goto :InstallWeboobDependances
)

:InstallWeboobDependances
echo.
echo 5.Install Weboob Dependances
echo.
echo -- cssselect
%PythonPath%Scripts\easy_install.exe cssselect || goto :InstallFailed
echo.
echo -- lxml
%PythonPath%Scripts\easy_install.exe lxml==3.2.5 || goto :InstallFailed
echo.
echo -- dateutils
%PythonPath%Scripts\easy_install.exe dateutils || goto :InstallFailed
echo.
echo -- pyyaml
%PythonPath%Scripts\easy_install.exe pyyaml || goto :InstallFailed
echo.
echo -- html2text
%PythonPath%Scripts\easy_install.exe html2text || goto :InstallFailed
echo.
echo -- mechanize
%PythonPath%Scripts\easy_install.exe mechanize || goto :InstallFailed
echo.
echo -- gdata
%PythonPath%Scripts\easy_install.exe gdata || goto :InstallFailed
echo.
echo -- feedparser
%PythonPath%Scripts\easy_install.exe feedparser || goto :InstallFailed
echo.
echo -- pillow
%PythonPath%Scripts\easy_install.exe pillow==2.3.0 || goto :InstallFailed
echo.
echo -- requests
%PythonPath%Scripts\easy_install.exe requests==2.3.0 || goto :InstallFailed

echo.
echo 6.Install WeBoob
%PythonPath%Scripts\easy_install.exe %WEBOOB% 	|| goto :InstallFailed

set StartupFolder=%AppData%\Microsoft\Windows\Start Menu\Programs
if exist "%StartupFolder%" Goto :FoundStartup
set StartupFolder=%UserProfile%\Start Menu\Programs
if exist "%StartupFolder%" Goto :FoundStartup
echo Cannot find Startup folder. 
echo do not create launchers
goto :InstallSucceed

:FoundStartup
if exist "%StartupFolder%\Weboob" (
	goto :CreateLauncher
) else (
	md "%StartupFolder%\Weboob"
	goto :CreateLauncher
)

:CreateLauncher
for %%i in (%LIST_APPLIQUATIONS_QT%) do ( 
	echo Process %%i

	(
	  echo @echo off
	  echo start %PythonPath%pythonw.exe %PythonPath%Scripts\%%i
	) > %%i.bat
	
	%PythonPath%python.exe convertPNG2ICO.py "%PythonPath%\Lib\site-packages\%WEBOOB%\share\icons\hicolor\64x64\apps\%%i.png" > nul
	
	if exist "%StartupFolder%\Weboob\%%i.exe" (
		del "%StartupFolder%\Weboob\%%i.exe"
	)

	"Bat_To_Exe_Converter_%ARCHITECTURE%.exe" -bat "%%i.bat" -save "%StartupFolder%\Weboob\%%i.exe" -icon "%PythonPath%\Lib\site-packages\%WEBOOB%\share\icons\hicolor\64x64\apps\%%i.ico" "%%i"
	del "%%i.bat"
	del "%PythonPath%\Lib\site-packages\%WEBOOB%\share\icons\hicolor\64x64\apps\%%i.ico"
)

goto :InstallSucceed

:InstallSucceed

del ez_setup.py
del convertPNG2ICO.py

echo.
echo INSTALLATION PROCESS SUCCEED
goto :Quit

:InstallFailed
echo.
echo INSTALLATION PROCESS FAILED
goto :Quit

:Quit
pause
