@echo off
REM 打包 Python 项目为单个可执行文件的批处理脚本

REM 设置项目主文件
set MAIN_SCRIPT=src\server.py

REM 设置 spec 文件生成目录
set SPEC_DIR=scripts

REM 设置输出目录
set OUTPUT_DIR=dist

REM 设置可执行文件名称
set EXE_NAME=DOUBAO_ASKED_QUICKLY

REM 执行打包命令（spec 文件生成到 scripts 目录）
pyinstaller ^
  --onefile ^
  --name %EXE_NAME% ^
  --specpath=%SPEC_DIR% ^
  --distpath %OUTPUT_DIR% ^
  --clean ^
  %MAIN_SCRIPT%

REM 检查打包是否成功
if %errorlevel% equ 0 (
  echo 打包成功！可执行文件位于 %OUTPUT_DIR% 目录下
  echo 可以在命令行中直接运行：%OUTPUT_DIR%\%EXE_NAME%.exe
  echo Spec 文件位于：%SPEC_DIR%\%EXE_NAME%.spec
) else (
  echo 打包失败，请检查错误信息
)
