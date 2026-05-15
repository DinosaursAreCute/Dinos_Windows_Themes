#Requires AutoHotkey v2.0
#SingleInstance Force


;
; Requires: VirtualDesktopAccessor.dll to be placed next to this script:
;   https://github.com/Ciantic/VirtualDesktopAccessor/releases
;

hVDA := DllCall("LoadLibrary", "Str", A_ScriptDir "VirtualDesktopAccessor.dll", "Ptr")
if !hVDA {
    MsgBox "VirtualDesktopAccessor.dll not found.`nPlace it in: " A_ScriptDir, "AutoKey Setup Error", "IconX"
    ExitApp
}

; Win+1 through Win+9: switch to workspace N (desktops are 0-indexed in the DLL)
#1:: GoToDesktop(1)
#2:: GoToDesktop(2)
#3:: GoToDesktop(3)
#4:: GoToDesktop(4)
#5:: GoToDesktop(5)
#6:: GoToDesktop(6)
#7:: GoToDesktop(7)
#8:: GoToDesktop(8)
#9:: GoToDesktop(9)

; Win+Shift+1 through Win+Shift+9: move active window to workspace N
#+1:: MoveToDesktop(1)
#+2:: MoveToDesktop(2)
#+3:: MoveToDesktop(3)
#+4:: MoveToDesktop(4)
#+5:: MoveToDesktop(5)
#+6:: MoveToDesktop(6)
#+7:: MoveToDesktop(7)
#+8:: MoveToDesktop(8)
#+9:: MoveToDesktop(9)

GoToDesktop(n) {
    DllCall("VirtualDesktopAccessor.dll\GoToDesktopNumber", "Int", n - 1, "Int")
}

MoveToDesktop(n) {
    hwnd := WinExist("A")
    DllCall("VirtualDesktopAccessor.dll\MoveWindowToDesktopNumber", "Ptr", hwnd, "Int", n - 1, "Int")
    DllCall("VirtualDesktopAccessor.dll\GoToDesktopNumber", "Int", n - 1, "Int")
}

