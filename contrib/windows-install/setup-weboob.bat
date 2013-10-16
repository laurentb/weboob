@echo off

call settings.cmd

echo.
echo 0.Set proxy
set/P HTTP_PROXY=Enter HTTP_PROXY if needed : 
set/P HTTPS_PROXY=Enter HTTPS_PROXY if needed :

echo.
echo 1.GNU/WGET Installation
for %%i in (wget.exe) do set wget=%%~$PATH:i
if not defined wget (
	wget-1.11.4-1-setup.exe
)

echo.
echo 2.Check Python 2.7 Installation
set KEY_NAME=HKLM\Software\Python\PythonCore\2.7\InstallPath
REG QUERY %KEY_NAME% > nul || 	(
									echo 2.1 Download Python 2.7
									wget -o python_donwload http://www.python.org/ftp/python/2.7.5/python-2.7.5.msi
									
									echo 2.2 Setup Python 2.7
									python-2.7.5.msi
									
									del python-2.7.5.msi
									del python_donwload
								)
								
for /F "tokens=4" %%A IN ('REG QUERY %KEY_NAME%') do (
    set PythonPath=%%A
)

echo.
echo 3.Check PyQt4 Installation
for %%i in (pyuic4.bat) do set qt=%%~$PATH:i
if not defined qt (

	echo 3.1 Download PyQt4
	wget -o qt_download http://downloads.sourceforge.net/project/pyqt/PyQt4/PyQt-4.10.3/PyQt4-4.10.3-gpl-Py2.7-Qt4.8.5-x32.exe?r=http%3A%2F%2Fsourceforge.net%2Fprojects%2Fpyqt%2Ffiles%2FPyQt4%2FPyQt-4.10.3%2F&ts=1380890340&use_mirror=garr

	echo 3.2 Setup PyQt4
	PyQt4-4.10.3-gpl-Py2.7-Qt4.8.5-x32.exe

	del PyQt4-4.10.3-gpl-Py2.7-Qt4.8.5-x32.exe
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
%PythonPath%Scripts\easy_install.exe lxml || goto :InstallFailed
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
echo -- pillow
%PythonPath%Scripts\easy_install.exe pillow || goto :InstallFailed

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
::for /f "delims=. tokens=1" %%i in ('dir /b "%PythonPath%\Lib\site-packages\%WEBOOB%\share\icons\hicolor\64x64\apps\q*.png"') do (
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

	"Bat_To_Exe_Converter.exe" -bat "%%i.bat" -save "%StartupFolder%\Weboob\%%i.exe" -icon "%PythonPath%\Lib\site-packages\%WEBOOB%\share\icons\hicolor\64x64\apps\%%i.ico" %%i"
	del "%%i.bat"
	del "%PythonPath%\Lib\site-packages\%WEBOOB%\share\icons\hicolor\64x64\apps\%%i.ico"
)

goto :InstallSucceed

:InstallSucceed
echo.
echo INSTALLATION PROCESS SUCCEED
goto :Quit

:InstallFailed
echo.
echo INSTALLATION PROCESS FAILED
goto :Quit

:Quit
pause