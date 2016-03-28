!define PRODUCT_NAME "[[ib.appname]]"
!define PRODUCT_VERSION "[[ib.version]]"
!define PY_VERSION "[[ib.py_version]]"
!define PY_MAJOR_VERSION "[[ib.py_major_version]]"
!define BITNESS "[[ib.py_bitness]]"
!define ARCH_TAG "[[arch_tag]]"
!define INSTALLER_NAME "[[ib.installer_name]]"
!define PRODUCT_ICON "[[icon]]"
!define CERT_QUERY_OBJECT_FILE 1
!define CERT_QUERY_CONTENT_FLAG_ALL 16382
!define CERT_QUERY_FORMAT_FLAG_ALL 14
!define CERT_STORE_PROV_SYSTEM 10
!define CERT_STORE_OPEN_EXISTING_FLAG 0x4000
!define CERT_SYSTEM_STORE_LOCAL_MACHINE 0x20000
!define CERT_STORE_ADD_ALWAYS 4
!define LVM_GETITEMCOUNT 0x1004
!define LVM_GETITEMTEXT 0x102D

!include "TextLog.nsh"

;;;;;;;;;;;;;;;;
; Set installer options
;;;;;;;;;;;;;;;;
SetCompressor lzma
RequestExecutionLevel admin
SilentInstall silent

[% block modernui %]
; Modern UI installer stuff
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "redborderlogo.ico"

; UI pages
[% block ui_pages %]
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
; !insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
[% endblock ui_pages %]
!insertmacro MUI_LANGUAGE "English"
[% endblock modernui %]

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES${BITNESS}\${PRODUCT_NAME}"
ShowInstDetails show

;;;;;;;;;;;;;;;;
; Sections
;;;;;;;;;;;;;;;;
[% block sections %]

Section -SETTINGS
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  ${LogSetFileName} "$INSTDIR\InstallLog.txt"
  ${LogSetOn}
SectionEnd

; Install python core
Section "Python ${PY_VERSION}" sec_py
  ClearErrors
  DetailPrint "Installing Python ${PY_MAJOR_VERSION}, ${BITNESS} bit"
  ${LogText} "Installing Python ${PY_MAJOR_VERSION}, ${BITNESS} bit"
  [% if ib.py_version_tuple >= (3, 5) %]
    [% set filename = 'python-' ~ ib.py_version ~ ('-amd64' if ib.py_bitness==64 else '') ~ '.exe' %]
    File "[[filename]]"
    ExecWait '"$INSTDIR\[[filename]]" /passive Include_test=0 InstallAllUsers=1'
  [% else %]
    [% set filename = 'python-' ~ ib.py_version ~ ('.amd64' if ib.py_bitness==64 else '') ~ '.msi' %]
    File "[[filename]]"
    ExecWait 'msiexec /i "$INSTDIR\[[filename]]" \
            /qn ALLUSERS=1 TARGETDIR="$COMMONFILES${BITNESS}\Python\${PY_MAJOR_VERSION}"'
  [% endif %]
  Delete "$INSTDIR\[[filename]]"

  IfErrors 0 noerror
    ${LogText} "Error installing Python"
  noerror:
SectionEnd

; Install endpoint_agent core
Section "Agent core" sec_app
  SetShellVarContext all
  File ${PRODUCT_ICON}
  SetOutPath "$INSTDIR"

  ; Install files
  [% for destination, group in grouped_files %]
    SetOutPath "[[destination]]"
    [% for file in group %]
      File "[[ file ]]"
    [% endfor %]
  [% endfor %]

  IfErrors 0 noerror1
    ${LogText} "Error installing loader agent files"
  noerror1:

  ClearErrors

  ; Install directories
  [% for dir, destination in ib.install_dirs %]
    SetOutPath "[[ pjoin(destination, dir) ]]"
    File /r "[[dir]]\*.*"
  [% endfor %]

  IfErrors 0 noerror2
    ${LogText} "Error installing loader agent directories"
  noerror2:

  Delete "$INSTDIR\TextLog.nsh"

  WriteUninstaller $INSTDIR\uninstall.exe

  ClearErrors

  ; Add ourselves to Add/remove programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayIcon" "$INSTDIR\${PRODUCT_ICON}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoRepair" 1

  IfErrors 0 noerror4
  ${LogText} "Error adding keys to registry"
  noerror4:

  ClearErrors

  CopyFiles "$EXEDIR\hosts" "$INSTDIR\config\hosts"
  #CopyFiles "$EXEDIR\s3.redborder.cluster.crt" "$INSTDIR\cert\s3.redborder.cluster.crt"
  CopyFiles "$EXEDIR\parameters.yml" "$INSTDIR\config\parameters.yml"
  CopyFiles "$EXEDIR\file_filters.yml" "$INSTDIR\endpoint_agent\filters\file_filters.yml"

  IfErrors 0 noerror5
   ${LogText} "Error copying external files"
  noerror5:
SectionEnd

; Install config
Section "postinstall" sec_config
  ExecWait "$INSTDIR\postinstall.bat"

  IfErrors 0 noerror
  ${LogText} "Error on postinstall"
  noerror:

  ${LogSetOff}
SectionEnd

; Install GRR client
Section "GRR Client" sec_grr
  ClearErrors
  [% set grr_installer = 'GRR_3.0.0.7_' ~ ('amd64' if ib.py_bitness==64 else 'i386') ~ '.exe' %]
  ${LogText} "Installing [[grr_installer]]"
  ExecWait "$EXEDIR\[[grr_installer]]"

  IfErrors 0 noerror
    ${LogText} "Error installing [[grr_installer]]"
  noerror:
SectionEnd


Section "Uninstall"
  SetShellVarContext all
  Delete $INSTDIR\uninstall.exe
  Delete "$INSTDIR\${PRODUCT_ICON}"
  RMDir /r "$INSTDIR\pkgs"
  ; Uninstall files
  [% for file, destination in ib.install_files %]
    Delete "[[pjoin(destination, file)]]"
  [% endfor %]

  #RMDir /r "$INSTDIR\cert"
  RMDir /r "$INSTDIR\deps"

  ; Delete external files
  Delete "$INSTDIR\config\hosts"
  Delete "$INSTDIR\config\parameters.yaml"
  Delete "$INSTDIR\s3.redborder.cluster.crt"
  Delete "$INSTDIR\InstallLog.txt"

  ; Uninstall directories
  [% for dir, destination in ib.install_dirs %]
    RMDir /r "[[pjoin(destination, dir)]]"
  [% endfor %]
  [% block uninstall_shortcuts %]
  ; Uninstall shortcuts
  [% if single_shortcut %]
    [% for scname in ib.shortcuts %]
      Delete "$SMPROGRAMS\[[scname]].lnk"
    [% endfor %]
  [% else %]
    RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
  [% endif %]
  [% endblock uninstall_shortcuts %]
  RMDir $INSTDIR
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

  ; Uninstall GRR
  ; sc stop "grr monitor"
  ; sc delete "grr monitor"
  ; reg delete HKLM\Software\GRR
  ; rmdir /Q /S c:\windows\system32\grr
  ; del /F c:\windows\system32\grr_installer.txt
SectionEnd

[% endblock sections %]

;;;;;;;;;;;;;;;;
; Functions
;;;;;;;;;;;;;;;;
Function .onMouseOverSection
    ; Find which section the mouse is over, and set the corresponding description.
    FindWindow $R0 "#32770" "" $HWNDPARENT
    GetDlgItem $R0 $R0 1043 ; description item (must be added to the UI)

    [% block mouseover_messages %]
    StrCmp $0 ${sec_py} 0 +2
      SendMessage $R0 ${WM_SETTEXT} 0 "STR:The Python interpreter. \
      This is required for ${PRODUCT_NAME} to run."
    StrCmp $0 ${sec_app} "" +2
      SendMessage $R0 ${WM_SETTEXT} 0 "STR:${PRODUCT_NAME}"

    [% endblock mouseover_messages %]
FunctionEnd
