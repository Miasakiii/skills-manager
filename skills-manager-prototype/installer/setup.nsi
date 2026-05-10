; Skills Manager - Windows 安装脚本 (NSIS 3.x)
; 使用方法: "C:\Program Files (x86)\NSIS\makensis.exe" setup.nsi

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "WordFunc.nsh"

!insertmacro WordReplace

; ── 基本信息 ────────────────────────────────────────────────
!define PRODUCT_NAME "Skills Manager"
!define PRODUCT_VERSION "0.1.0"
!define PRODUCT_PUBLISHER "Skills Manager"
!define PRODUCT_WEB_SITE "https://github.com/user/skills-manager"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

SetCompressor /SOLID lzma
SetCompressorDictSize 64
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\dist\skills-manager-setup.exe"
InstallDir "$PROGRAMFILES\Skills Manager"
InstallDirRegKey HKLM "${PRODUCT_UNINST_KEY}" "InstallLocation"
RequestExecutionLevel admin

; ── Modern UI 配置 ──────────────────────────────────────────
!define MUI_ABORTWARNING

!define MUI_WELCOMEPAGE_TITLE "Skills Manager ${PRODUCT_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "本向导将引导您完成 Skills Manager 的安装。$\r$\n$\r$\nSkills Manager 是一套 AI Skill 格式转换与管理工具，包含命令行工具和桌面应用。"

!define MUI_FINISHPAGE_RUN "$INSTDIR\skills-manager-desktop.exe"
!define MUI_FINISHPAGE_RUN_TEXT "启动 Skills Manager 桌面应用"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

; ── 安装区段 ────────────────────────────────────────────────

Section "Skills Manager (必需)" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"

  File "..\dist\skills-manager-desktop.exe"
  File "..\dist\skills-manager-cli.exe"

  SetOutPath "$INSTDIR\examples"
  File /r "..\examples\*"

  SetOutPath "$INSTDIR"

  ; 开始菜单快捷方式
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Skills Manager.lnk" "$INSTDIR\skills-manager-desktop.exe"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Skills Manager CLI.lnk" "$INSTDIR\skills-manager-cli.exe"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\uninst.exe"

  ; 桌面快捷方式
  CreateShortCut "$DESKTOP\Skills Manager.lnk" "$INSTDIR\skills-manager-desktop.exe"

  ; 卸载注册表
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME} ${PRODUCT_VERSION}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\skills-manager-desktop.exe"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoRepair" 1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "EstimatedSize" "$0"

  ; ── 添加 CLI 到系统 PATH ────────────────────────────────
  ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
  StrCpy $1 "$INSTDIR"
  ${WordReplace} "$0" ";$1" "" "+" $2
  ${If} $0 == $2
    ; 未在 PATH 中，追加
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$0;$INSTDIR"
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000
  ${EndIf}

  WriteUninstaller "$INSTDIR\uninst.exe"
SectionEnd

; ── .skill 文件关联 ─────────────────────────────────────────

Section "关联 .skill 文件" SecFileAssoc
  WriteRegStr HKCR ".skill" "" "SkillsManager.SkillPackage"
  WriteRegStr HKCR "SkillsManager.SkillPackage" "" "Skills Manager Skill Package"
  WriteRegStr HKCR "SkillsManager.SkillPackage\DefaultIcon" "" "$INSTDIR\skills-manager-desktop.exe,0"
  WriteRegStr HKCR "SkillsManager.SkillPackage\shell\open\command" "" '"$INSTDIR\skills-manager-cli.exe" install "%1"'
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "安装 Skills Manager 的主程序和命令行工具。"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecFileAssoc} "将 .skill 文件关联到 Skills Manager，双击即可安装。"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ── 卸载区段 ────────────────────────────────────────────────

Section "Uninstall"
  Delete "$INSTDIR\skills-manager-desktop.exe"
  Delete "$INSTDIR\skills-manager-cli.exe"
  Delete "$INSTDIR\uninst.exe"
  RMDir /r "$INSTDIR\examples"
  RMDir "$INSTDIR"

  Delete "$DESKTOP\Skills Manager.lnk"
  RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"

  DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKCR ".skill"
  DeleteRegKey HKCR "SkillsManager.SkillPackage"

  ; 从 PATH 移除
  ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
  ${WordReplace} "$0" ";$INSTDIR" "" "+" $1
  ${WordReplace} "$1" "$INSTDIR;" "" "+" $2
  WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$2"
  SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000

  SetAutoClose true
SectionEnd
