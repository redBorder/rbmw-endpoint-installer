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

;;;;;;;;;;;;;;;;
; Define macros
;;;;;;;;;;;;;;;;
!define FileJoin `!insertmacro FileJoinCall`
!macro FileJoinCall _FILE1 _FILE2 _FILE3
  Push `${_FILE1}`
  Push `${_FILE2}`
  Push `${_FILE3}`
  Call FileJoin
!macroend

;;;;;;;;;;;;;;;;
; Set installer options
;;;;;;;;;;;;;;;;
SetCompressor lzma
RequestExecutionLevel admin
; SilentInstall silent

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

;;;;;;;;;;;;;;;;
; Sections
;;;;;;;;;;;;;;;;
[% block sections %]

Section -SETTINGS
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
SectionEnd

; Install python
Section /o "Python ${PY_VERSION}" sec_py
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

; Install GRR client
Section /o "GRR Client" sec_grr
  ExecWait "$INSTDIR\grr\GRR_3.0.0.7_amd64.exe"
SectionEnd

; Install certificates
Section /o "redBorder root certificate" sec_cert
  Push "$INSTDIR\certs\s3.redborder.cluster.crt"
  Call AddCertificateToStore
  Pop $0
  ${If} $0 != success
  MessageBox MB_OK "import failed: $0"
  ${EndIf}
SectionEnd

; Add entries to host
Section /o "Add entries to hosts files" sec_host
  ${FileJoin} "$SYSDIR\drivers\etc\hosts" "$INSTDIR\hosts" "$SYSDIR\drivers\etc\hosts"
SectionEnd

; Install endpoint_agent as a service
Section "Install as a services" sec_service
  nsExec::Exec "cmd"
SectionEnd

; Install endpoint_agent
Section "Loader Agent" sec_app
  SectionIn RO
  SetShellVarContext all
  File ${PRODUCT_ICON}
  SetOutPath "$INSTDIR\pkgs"
  File /r "pkgs\*.*"
  SetOutPath "$INSTDIR"

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

Function FileJoin
	Exch $2
	Exch
	Exch $1
	Exch
	Exch 2
	Exch $0
	Exch 2
	Push $3
	Push $4
	Push $5
	ClearErrors

	IfFileExists $0 0 error
	IfFileExists $1 0 error
	StrCpy $3 0
	IntOp $3 $3 - 1
	StrCpy $4 $2 1 $3
	StrCmp $4 \ +2
	StrCmp $4 '' +3 -3
	StrCpy $4 $2 $3
	IfFileExists '$4\*.*' 0 error

	StrCmp $2 $0 0 +2
	StrCpy $2 ''
	StrCmp $2 '' 0 +3
	StrCpy $4 $0
	goto +3
	GetTempFileName $4
	CopyFiles /SILENT $0 $4
	FileOpen $3 $4 a
	IfErrors error
	FileSeek $3 -1 END
	FileRead $3 $5
	StrCmp $5 '$\r' +3
	StrCmp $5 '$' +2
	FileWrite $3 '$\r$'

	;FileWrite $3 '$\r$--Divider--$\r$'

	FileOpen $0 $1 r
	IfErrors error
	FileRead $0 $5
	IfErrors +3
	FileWrite $3 $5
	goto -3
	FileClose $0
	FileClose $3
	StrCmp $2 '' end
	Delete '$EXEDIR\$2'
	Rename $4 '$EXEDIR\$2'
	IfErrors 0 end
	Delete $2
	Rename $4 $2
	IfErrors 0 end

	error:
	SetErrors

	end:
	Pop $5
	Pop $4
	Pop $3
	Pop $2
	Pop $1
	Pop $0
FunctionEnd
