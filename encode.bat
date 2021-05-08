@echo off
rem ***************************************
rem 処理名：動画一括圧縮処理 (FFmpeg)
rem   作成日：2020/08/09
rem   更新日：2020/08/09
rem   作成者: じゃぶじゃぶ
rem
rem ***************************************


rem ------------------------------
rem ffmpegの出力オプションの初期値を設定  （※変更可）
rem  オプションを指定しない場合は、イコール後に空欄を設定
rem ------------------------------
rem 圧縮する対象があるフォルダを指定(デフォルト:C:\sample\)
set INPUT_FOLDER=
rem コーディックを指定(例:libx264)
set CODEC=
rem ビットレートを指定(例:640k)
set BIT_RATE=
rem フレームレートを指定(例:120)
set FRAME_RATE=
rem サイズを指定（例:1280x720）
set SIZE=
rem 圧縮率を指定（例:10）
set COMPRESSION_RATE=
rem 圧縮対象の拡張子（例:mp4）
set EXTENSION=mp4




rem =========================================
rem ------------------------------
rem ↓↓↓↓ 以下 動画圧縮のメイン処理↓↓↓
rem      ※変更厳禁！！
rem ------------------------------

rem ----対話式による出力パラメータの指定 ----
set /p PARAM="圧縮する対象フォルダは？(デフォルト:%INPUT_FOLDER%) ："
if not ""%PARAM%"" == """" (
  set INPUT_FOLDER=%PARAM%
  set PARAM=
)
set /p PARAM="コーディックをは？(例:libx264、またはlibx265 デフォルト：%CODEC%) ："
if not ""%PARAM%"" == """" (
  set CODEC=%PARAM%
  set PARAM=
)
set /p PARAM="ビットレートは？(例:640k デフォルト：%BIT_RATE%) ："
if not ""%PARAM%"" == """" (
  set BIT_RATE=%PARAM%
  set PARAM=
)
set /p PARAM="フレームレートは？(例:120 デフォルト：%FRAME_RATE%) ："
if not ""%PARAM%"" == """" (
  set FRAME_RATE=%PARAM%
  set PARAM=
)
set /p PARAM="サイズは？（例:1280x720 デフォルト：%SIZE%）："
if not ""%PARAM%"" == """" (
  set SIZE=%PARAM%
  set PARAM=
)
set /p PARAM="圧縮対象の拡張子は？（例:mp4 デフォルト：%EXTENSION%）："
if not ""%PARAM%"" == """" (
  set EXTENSION=%PARAM%
  set PARAM=
)

rem ---- 出力オプションの作成 ----
rem チェックフラグ
set CHEK_FLAG=T
rem 出力オプションの解析
set OUTPUT_OPTIONS=

rem 出力先オプションの有無確認
set CURRENT_DIRECTORY=%CD%
  set baka=%CD%

if ""%INPUT_FOLDER%"" == """" (
  rem カレントディレクトリを設定
  set INPUT_FOLDER=%CD%
) else (
  rem ディレクトリの有無確認
  IF NOT EXIST "%INPUT_FOLDER%" (
    set CHEK_FLAG=F
    echo 圧縮対象のフォルダが存在しませんでした。（%INPUT_FOLDER%）
  )
)
rem コーディックオプションの有無確認
if not ""%CODEC%"" == """" (
  echo %CODEC% | find "libx26" >NUL
  if NOT ERRORLEVEL 1 (
    set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -vcodec %CODEC%
  ) ELSE (
    set CHEK_FLAG=F
    echo ”libx264、またはlibx265”で指定してください
  )
)
rem ビットレートオプションの有無確認
if not ""%BIT_RATE%"" == """" (
  echo %BIT_RATE% | find "k" >NUL
  if NOT ERRORLEVEL 1 (
    set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -b:v %BIT_RATE%
  ) ELSE (
    set CHEK_FLAG=F
    echo ”kb/s”で指定してください（例:1200k）
  )
)
rem フレームレートオプションの有無確認
if not ""%FRAME_RATE%"" == """" (
  set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -r %FRAME_RATE%
)
rem サイズオプションの有無確認
if not ""%SIZE%"" == """" (
  echo %SIZE% | find "x" >NUL
  if NOT ERRORLEVEL 1 (
    set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -s %SIZE%
  ) ELSE (
    set CHEK_FLAG=F
    echo ”横ピクセルx縦ピクセル”で指定してください（例:1280x720）
  )
)
rem 圧縮率オプションの有無確認
if not ""%COMPRESSION_RATE%"" == """" (
  set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -crf %COMPRESSION_RATE%
)
rem 拡張子オプションの有無確認
if ""%EXTENSION%"" == """" (
  set CHEK_FLAG=F
  echo 圧縮する対象の拡張子を指定してください。
)


rem ----圧縮対象のフォルダから動画ファイルを抽出 ----
rem 出力先のフォルダの存在チェック
set OUTPUT_FOLDER=%INPUT_FOLDER%\comp\
set OUTPUT_FILE=%INPUT_FOLDER%\*.%EXTENSION%
if %CHEK_FLAG%==T (
  if not exist "%OUTPUT_FOLDER%" (
    echo 出力先フォルダが存在しなかったため作成（%OUTPUT_FOLDER%）
    rem 出力先フォルダが存在しない場合は作成する
    mkdir %OUTPUT_FOLDER%
  )

  setlocal enabledelayedexpansion

  rem 出力先のファイル一覧を取得
  for /f "usebackq" %%i in (`dir %OUTPUT_FILE% /B`) do (
    for /f "usebackq tokens=1 delims=." %%x in (`echo %%i`) do (
      rem ffmpegによる圧縮処理を実行
      rem 実行するコマンドをコンソールに出力
      rem 時間のスペースを0に置換
      set tmptime=!time: =0!
      echo ffmpeg -i %INPUT_FOLDER%\%%i %OUTPUT_OPTIONS% %OUTPUT_FOLDER%%%x_mini_!date:~0,4!!date:~5,2!!date:~8,2!!tmptime:~0,2!!tmptime:~3,2!!tmptime:~6,2!.%EXTENSION%
      echo ....
      ffmpeg -i %INPUT_FOLDER%\%%i %OUTPUT_OPTIONS% %OUTPUT_FOLDER%%%x_mini_!date:~0,4!!date:~5,2!!date:~8,2!!tmptime:~0,2!!tmptime:~3,2!!tmptime:~6,2!.%EXTENSION%
      echo %%iの動画圧縮処理が完了しました。（時刻：!date! !time!）
      echo ----------
    )
  )

  endlocal

  echo 圧縮処理が全て正常に完了しました。
) else (
  echo オプションの指定に不備があったため、処理を中断しました。

)

rem ---- 初期化 ----
call :setting
pause >nul




rem -----------------------------
rem 環境変数の初期化処理
rem -----------------------------
:setting
  rem 初期化処理
  set INPUT_FOLDER=
  set CODEC=
  set BIT_RATE=
  set FRAME_RATE=
  set SIZE=
  set COMPRESSION_RATE=
  set EXTENSION=
  set OUTPUT_OPTIONS=
  set OUTPUT_FOLDER=
  set OUTPUT_FILE=
  set CHEK_FLAG=
  set PARAM=
  set CURRENT_DIRECTORY=
exit /b 1
