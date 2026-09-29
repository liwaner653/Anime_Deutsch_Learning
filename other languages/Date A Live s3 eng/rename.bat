@echo off
setlocal enabledelayedexpansion
set num=1
for %%f in (*.srt) do (
    if not "%%~nf"=="rename" (
        ren "%%f" "!num!%%~xf"
        set /a num+=1
    )
)
echo 重命名完成！
pause