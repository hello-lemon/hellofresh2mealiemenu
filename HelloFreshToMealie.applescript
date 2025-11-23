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

-- Demander les semaines (sélection multiple)
set weekChoices to {"Semaine actuelle", "Semaine prochaine", "Dans 2 semaines"}
set selectedWeeks to choose from list weekChoices with title "Sélection des semaines" with prompt "Sélectionne une ou plusieurs semaines à planifier :" default items {"Semaine actuelle"} OK button name "OK" cancel button name "Annuler" with multiple selections allowed

if selectedWeeks is false then
	-- Utilisateur a annulé
	return
end if

-- Convertir les choix en offsets
set weekOffsets to {}
repeat with weekChoice in selectedWeeks
	if weekChoice is "Semaine actuelle" then
		set end of weekOffsets to "0"
	else if weekChoice is "Semaine prochaine" then
		set end of weekOffsets to "1"
	else if weekChoice is "Dans 2 semaines" then
		set end of weekOffsets to "2"
	end if
end repeat

-- Construire la commande
if (count of weekOffsets) > 1 then
	-- Plusieurs semaines : utiliser --weeks
	set weeksArg to my joinList(weekOffsets, ",")
	set cmd to "cd " & quoted form of scriptPath & " && ./run.sh -m " & quoted form of magicLink & " --weeks " & weeksArg
else
	-- Une seule semaine : utiliser -w
	set cmd to "cd " & quoted form of scriptPath & " && ./run.sh -m " & quoted form of magicLink & " -w " & item 1 of weekOffsets
end if

-- Lancer dans le Terminal
tell application "Terminal"
	activate
	do script cmd
end tell

-- Fonction helper pour joindre une liste
on joinList(theList, theDelimiter)
	set oldDelimiters to AppleScript's text item delimiters
	set AppleScript's text item delimiters to theDelimiter
	set theString to theList as string
	set AppleScript's text item delimiters to oldDelimiters
	return theString
end joinList
