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

SetCompressor lzma

RequestExecutionLevel admin

[% block modernui %]
; Modern UI installer stuff
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "redborderlogo.ico"

; UI pages
[% block ui_pages %]
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
[% endblock ui_pages %]
!insertmacro MUI_LANGUAGE "English"
[% endblock modernui %]

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES${BITNESS}\${PRODUCT_NAME}"
ShowInstDetails show

Section -SETTINGS
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
SectionEnd

[% block sections %]

Section "Python ${PY_VERSION}" sec_py
  DetailPrint "Installing Python ${PY_MAJOR_VERSION}, ${BITNESS} bit"
  [% if ib.py_version_tuple >= (3, 5) %]
    [% set filename = 'python-' ~ ib.py_version ~ ('-amd64' if ib.py_bitness==64 else '') ~ '.exe' %]
    File "[[filename]]"
    ExecWait '"$INSTDIR\[[filename]]" /passive Include_test=0 InstallAllUsers=1'
  [% else %]
    [% set filename = 'python-' ~ ib.py_version ~ ('.amd64' if ib.py_bitness==64 else '') ~ '.msi' %]
    File "[[filename]]"
    ExecWait 'msiexec /i "$INSTDIR\[[filename]]" \
            /qb ALLUSERS=1 TARGETDIR="$COMMONFILES${BITNESS}\Python\${PY_MAJOR_VERSION}"'
  [% endif %]
  Delete "$INSTDIR\[[filename]]"
SectionEnd

Section "!${PRODUCT_NAME}" sec_app
  SectionIn RO
  SetShellVarContext all
  File ${PRODUCT_ICON}
  SetOutPath "$INSTDIR\pkgs"
  File /r "pkgs\*.*"
  SetOutPath "$INSTDIR"

  ; Write to hosts file
  ;FileOpen $4 "$DESKTOP\SomeFile.txt" a
  FileOpen $4 $SYSDIR\drivers\etc\hosts a
  FileSeek $4 0 END
  FileWrite $4 "$\r$\n" ; we write a new line
  FileWrite $4 "10.0.161.211     rbmqsp2ndx5r rbmqsp2ndx5r.redborder.cluster rbmqsp2ndx5r-0$\r$\n"
  FileWrite $4 "10.0.161.211     riak.redborder.cluster s3.redborder.cluster redborder.s3.redborder.cluster riak-cs.s3.redborder.cluster$\r$\n"
  FileWrite $4 "10.0.161.211     rb-webui.redborder.cluster$\r$\n"
  FileWrite $4 "10.0.161.211     s3.redborder.cluster malware.s3.redborder.cluster$\r$\n"
  FileWrite $4 "$\r$\n" ; we write an extra line
  FileClose $4 ; and close the file

  ; Install files
  [% for destination, group in grouped_files %]
    SetOutPath "[[destination]]"
    [% for file in group %]
      File "[[ file ]]"
    [% endfor %]
  [% endfor %]

  ; Install directories
  [% for dir, destination in ib.install_dirs %]
    SetOutPath "[[ pjoin(destination, dir) ]]"
    File /r "[[dir]]\*.*"
  [% endfor %]

  [% block install_shortcuts %]
  ; Install shortcuts
  ; The output path becomes the working directory for shortcuts
  SetOutPath "%HOMEDRIVE%\%HOMEPATH%"
  [% if single_shortcut %]
    [% for scname, sc in ib.shortcuts.items() %]
    CreateShortCut "$SMPROGRAMS\[[scname]].lnk" "[[sc['target'] ]]" \
      '[[ sc['parameters'] ]]' "$INSTDIR\[[ sc['icon'] ]]"
    [% endfor %]
  [% else %]
    [# Multiple shortcuts: create a directory for them #]
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    [% for scname, sc in ib.shortcuts.items() %]
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\[[scname]].lnk" "[[sc['target'] ]]" \
      '[[ sc['parameters'] ]]' "$INSTDIR\[[ sc['icon'] ]]"
    [% endfor %]
  [% endif %]
  SetOutPath "$INSTDIR"
  [% endblock install_shortcuts %]

  ; Byte-compile Python files.
  DetailPrint "Byte-compiling Python modules..."
  nsExec::ExecToLog '[[ python ]] -m compileall -q "$INSTDIR\pkgs"'
  WriteUninstaller $INSTDIR\uninstall.exe
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

  ; Install certificates
  Push "$INSTDIR\certs\s3.redborder.cluster.crt"
  Call AddCertificateToStore
  Pop $0
  ${If} $0 != success
   MessageBox MB_OK "import failed: $0"
  ${EndIf}

  ; Check if we need to reboot
  IfRebootFlag 0 noreboot
    MessageBox MB_YESNO "A reboot is required to finish the installation. Do you wish to reboot now?" \
                /SD IDNO IDNO noreboot
      Reboot
  noreboot:
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
SectionEnd

[% endblock sections %]

; Functions

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

Function AddCertificateToStore
  Exch $0
  Push $1
  Push $R0

  System::Call "crypt32::CryptQueryObject(i ${CERT_QUERY_OBJECT_FILE}, w r0, \
    i ${CERT_QUERY_CONTENT_FLAG_ALL}, i ${CERT_QUERY_FORMAT_FLAG_ALL}, \
    i 0, i 0, i 0, i 0, i 0, i 0, *i .r0) i .R0"

  ${If} $R0 <> 0
    System::Call "crypt32::CertOpenStore(i ${CERT_STORE_PROV_SYSTEM}, i 0, i 0, \
      i ${CERT_STORE_OPEN_EXISTING_FLAG}|${CERT_SYSTEM_STORE_LOCAL_MACHINE}, \
      w 'ROOT') i .r1"
    ${If} $1 <> 0
      System::Call "crypt32::CertAddCertificateContextToStore(i r1, i r0, \
        i ${CERT_STORE_ADD_ALWAYS}, i 0) i .R0"
      System::Call "crypt32::CertFreeCertificateContext(i r0)"
      ${If} $R0 = 0
        StrCpy $0 "Unable to add certificate to certificate store"
      ${Else}
        StrCpy $0 "success"
      ${EndIf}
      System::Call "crypt32::CertCloseStore(i r1, i 0)"
    ${Else}
      System::Call "crypt32::CertFreeCertificateContext(i r0)"
      StrCpy $0 "Unable to open certificate store"
    ${EndIf}

  ${Else}
    StrCpy $0 "Unable to open certificate file"
  ${EndIf}

  Pop $R0
  Pop $1
  Exch $0
FunctionEnd
