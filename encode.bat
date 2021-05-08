@echo off
rem ***************************************
rem �������F����ꊇ���k���� (FFmpeg)
rem   �쐬���F2020/08/09
rem   �X�V���F2020/08/09
rem   �쐬��: ����Ԃ����
rem
rem ***************************************


rem ------------------------------
rem ffmpeg�̏o�̓I�v�V�����̏����l��ݒ�  �i���ύX�j
rem  �I�v�V�������w�肵�Ȃ��ꍇ�́A�C�R�[����ɋ󗓂�ݒ�
rem ------------------------------
rem ���k����Ώۂ�����t�H���_���w��(�f�t�H���g:C:\sample\)
set INPUT_FOLDER=
rem �R�[�f�B�b�N���w��(��:libx264)
set CODEC=
rem �r�b�g���[�g���w��(��:640k)
set BIT_RATE=
rem �t���[�����[�g���w��(��:120)
set FRAME_RATE=
rem �T�C�Y���w��i��:1280x720�j
set SIZE=
rem ���k�����w��i��:10�j
set COMPRESSION_RATE=
rem ���k�Ώۂ̊g���q�i��:mp4�j
set EXTENSION=mp4




rem =========================================
rem ------------------------------
rem �������� �ȉ� ���戳�k�̃��C������������
rem      ���ύX���ցI�I
rem ------------------------------

rem ----�Θb���ɂ��o�̓p�����[�^�̎w�� ----
set /p PARAM="���k����Ώۃt�H���_�́H(�f�t�H���g:%INPUT_FOLDER%) �F"
if not ""%PARAM%"" == """" (
  set INPUT_FOLDER=%PARAM%
  set PARAM=
)
set /p PARAM="�R�[�f�B�b�N���́H(��:libx264�A�܂���libx265 �f�t�H���g�F%CODEC%) �F"
if not ""%PARAM%"" == """" (
  set CODEC=%PARAM%
  set PARAM=
)
set /p PARAM="�r�b�g���[�g�́H(��:640k �f�t�H���g�F%BIT_RATE%) �F"
if not ""%PARAM%"" == """" (
  set BIT_RATE=%PARAM%
  set PARAM=
)
set /p PARAM="�t���[�����[�g�́H(��:120 �f�t�H���g�F%FRAME_RATE%) �F"
if not ""%PARAM%"" == """" (
  set FRAME_RATE=%PARAM%
  set PARAM=
)
set /p PARAM="�T�C�Y�́H�i��:1280x720 �f�t�H���g�F%SIZE%�j�F"
if not ""%PARAM%"" == """" (
  set SIZE=%PARAM%
  set PARAM=
)
set /p PARAM="���k�Ώۂ̊g���q�́H�i��:mp4 �f�t�H���g�F%EXTENSION%�j�F"
if not ""%PARAM%"" == """" (
  set EXTENSION=%PARAM%
  set PARAM=
)

rem ---- �o�̓I�v�V�����̍쐬 ----
rem �`�F�b�N�t���O
set CHEK_FLAG=T
rem �o�̓I�v�V�����̉��
set OUTPUT_OPTIONS=

rem �o�͐�I�v�V�����̗L���m�F
set CURRENT_DIRECTORY=%CD%
  set baka=%CD%

if ""%INPUT_FOLDER%"" == """" (
  rem �J�����g�f�B���N�g����ݒ�
  set INPUT_FOLDER=%CD%
) else (
  rem �f�B���N�g���̗L���m�F
  IF NOT EXIST "%INPUT_FOLDER%" (
    set CHEK_FLAG=F
    echo ���k�Ώۂ̃t�H���_�����݂��܂���ł����B�i%INPUT_FOLDER%�j
  )
)
rem �R�[�f�B�b�N�I�v�V�����̗L���m�F
if not ""%CODEC%"" == """" (
  echo %CODEC% | find "libx26" >NUL
  if NOT ERRORLEVEL 1 (
    set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -vcodec %CODEC%
  ) ELSE (
    set CHEK_FLAG=F
    echo �hlibx264�A�܂���libx265�h�Ŏw�肵�Ă�������
  )
)
rem �r�b�g���[�g�I�v�V�����̗L���m�F
if not ""%BIT_RATE%"" == """" (
  echo %BIT_RATE% | find "k" >NUL
  if NOT ERRORLEVEL 1 (
    set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -b:v %BIT_RATE%
  ) ELSE (
    set CHEK_FLAG=F
    echo �hkb/s�h�Ŏw�肵�Ă��������i��:1200k�j
  )
)
rem �t���[�����[�g�I�v�V�����̗L���m�F
if not ""%FRAME_RATE%"" == """" (
  set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -r %FRAME_RATE%
)
rem �T�C�Y�I�v�V�����̗L���m�F
if not ""%SIZE%"" == """" (
  echo %SIZE% | find "x" >NUL
  if NOT ERRORLEVEL 1 (
    set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -s %SIZE%
  ) ELSE (
    set CHEK_FLAG=F
    echo �h���s�N�Z��x�c�s�N�Z���h�Ŏw�肵�Ă��������i��:1280x720�j
  )
)
rem ���k���I�v�V�����̗L���m�F
if not ""%COMPRESSION_RATE%"" == """" (
  set OUTPUT_OPTIONS=%OUTPUT_OPTIONS% -crf %COMPRESSION_RATE%
)
rem �g���q�I�v�V�����̗L���m�F
if ""%EXTENSION%"" == """" (
  set CHEK_FLAG=F
  echo ���k����Ώۂ̊g���q���w�肵�Ă��������B
)


rem ----���k�Ώۂ̃t�H���_���瓮��t�@�C���𒊏o ----
rem �o�͐�̃t�H���_�̑��݃`�F�b�N
set OUTPUT_FOLDER=%INPUT_FOLDER%\comp\
set OUTPUT_FILE=%INPUT_FOLDER%\*.%EXTENSION%
if %CHEK_FLAG%==T (
  if not exist "%OUTPUT_FOLDER%" (
    echo �o�͐�t�H���_�����݂��Ȃ��������ߍ쐬�i%OUTPUT_FOLDER%�j
    rem �o�͐�t�H���_�����݂��Ȃ��ꍇ�͍쐬����
    mkdir %OUTPUT_FOLDER%
  )

  setlocal enabledelayedexpansion

  rem �o�͐�̃t�@�C���ꗗ���擾
  for /f "usebackq" %%i in (`dir %OUTPUT_FILE% /B`) do (
    for /f "usebackq tokens=1 delims=." %%x in (`echo %%i`) do (
      rem ffmpeg�ɂ�鈳�k���������s
      rem ���s����R�}���h���R���\�[���ɏo��
      rem ���Ԃ̃X�y�[�X��0�ɒu��
      set tmptime=!time: =0!
      echo ffmpeg -i %INPUT_FOLDER%\%%i %OUTPUT_OPTIONS% %OUTPUT_FOLDER%%%x_mini_!date:~0,4!!date:~5,2!!date:~8,2!!tmptime:~0,2!!tmptime:~3,2!!tmptime:~6,2!.%EXTENSION%
      echo ....
      ffmpeg -i %INPUT_FOLDER%\%%i %OUTPUT_OPTIONS% %OUTPUT_FOLDER%%%x_mini_!date:~0,4!!date:~5,2!!date:~8,2!!tmptime:~0,2!!tmptime:~3,2!!tmptime:~6,2!.%EXTENSION%
      echo %%i�̓��戳�k�������������܂����B�i�����F!date! !time!�j
      echo ----------
    )
  )

  endlocal

  echo ���k�������S�Đ���Ɋ������܂����B
) else (
  echo �I�v�V�����̎w��ɕs�������������߁A�����𒆒f���܂����B

)

rem ---- ������ ----
call :setting
pause >nul




rem -----------------------------
rem ���ϐ��̏���������
rem -----------------------------
:setting
  rem ����������
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
