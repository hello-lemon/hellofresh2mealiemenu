#!/usr/bin/osascript
-- Interface AppleScript native pour macOS
-- Double-click pour lancer

set scriptPath to (do shell script "dirname " & quoted form of POSIX path of (path to me))

-- Demander le magic link
set magicLink to text returned of (display dialog "Colle le magic link HelloFresh :" default answer "" with title "HelloFresh → Mealie" buttons {"Annuler", "OK"} default button "OK" with icon note)

if magicLink is "" then
	display dialog "Erreur : Le magic link est vide" buttons {"OK"} default button "OK" with icon stop
	return
end if

-- Demander la semaine
set weekChoice to button returned of (display dialog "Quelle semaine ?" buttons {"Cette semaine", "Semaine prochaine", "Dans 2 semaines"} default button "Cette semaine" with icon note)

set weekOffset to 0
if weekChoice is "Semaine prochaine" then
	set weekOffset to 1
else if weekChoice is "Dans 2 semaines" then
	set weekOffset to 2
end if

-- Construire la commande
set cmd to "cd " & quoted form of scriptPath & " && ./run.sh -m " & quoted form of magicLink & " -w " & weekOffset

-- Lancer dans le Terminal
tell application "Terminal"
	activate
	do script cmd
end tell
