// Lernset anlegen und bearbeiten: normale Karten und Drei-Formen-Pakete.
// Die Triple-Karten werden vom Core erzeugt (sets.tripleKarten), damit
// Anzeige und Speicherformat garantiert zusammenpassen.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import theme
import "components"

Dialog {
    id: dlg
    modal: true
    title: bearbeitet ? "Lernset bearbeiten" : "Neues Lernset"
    width: 660
    height: 640
    closePolicy: Popup.CloseOnEscape

    property string lernsetId: ""
    property string zielOrdner: ""
    property bool bearbeitet: lernsetId !== ""

    signal gespeichert(string lernsetId)

    ListModel { id: karten }

    function oeffnenNeu(ordner) {
        lernsetId = ""
        zielOrdner = ordner
        nameFeld.text = ""
        karten.clear()
        open()
        nameFeld.forceActiveFocus()
    }

    function oeffnenBearbeiten(id) {
        var daten = sets.lernsetLaden(id)
        if (!daten || !daten.id) return
        lernsetId = daten.id
        zielOrdner = daten.ordner
        nameFeld.text = daten.name
        karten.clear()
        for (var i = 0; i < daten.items.length; i++)
            karten.append({ q: daten.items[i].q, a: daten.items[i].a })
        open()
        nameFeld.forceActiveFocus()
    }

    // Von aussen aufrufbar, damit sich der Einfuege-Dialog auch ohne Klick
    // oeffnen laesst - gebraucht beim Pruefen der Darstellung.
    function textImportOeffnen() {
        textImport.oeffnen()
    }

    function kartenAlsListe() {
        var out = []
        for (var i = 0; i < karten.count; i++) {
            var k = karten.get(i)
            out.push({ q: k.q, a: k.a })
        }
        return out
    }

    function normaleKarteHinzufuegen() {
        var q = frageFeld.text.trim()
        var a = antwortFeld.text.trim().toLowerCase()
        if (q === "" || a === "") return
        karten.append({ q: q, a: a })
        frageFeld.text = ""
        antwortFeld.text = ""
        frageFeld.forceActiveFocus()
        kartenListe.positionViewAtEnd()
    }

    function tripleHinzufuegen() {
        var neu = sets.tripleKarten(form1.text, form2.text, form3.text)
        if (!neu || neu.length !== 3) return
        for (var i = 0; i < neu.length; i++)
            karten.append({ q: neu[i].q, a: neu[i].a })
        form1.text = ""; form2.text = ""; form3.text = ""
        form1.forceActiveFocus()
        kartenListe.positionViewAtEnd()
    }

    function speichern() {
        var id = bearbeitet
            ? sets.lernsetSpeichern(lernsetId, nameFeld.text, kartenAlsListe())
            : sets.lernsetAnlegenIn(zielOrdner, nameFeld.text, kartenAlsListe())
        if (id !== "") {
            gespeichert(id)
            close()
        }
    }

    background: Rectangle {
        color: Theme.background
        radius: Theme.radiusGross
        border.color: Theme.border
        border.width: 1
    }
    header: Text {
        text: dlg.title
        color: Theme.textPrimary
        font.pixelSize: Theme.schriftL
        font.bold: true
        padding: Theme.abstandM
    }

    contentItem: ColumnLayout {
        spacing: Theme.abstandS

        // -- Name -------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.abstandS
            Text {
                text: "Name"
                color: Theme.textSecondary
                font.pixelSize: Theme.schriftS
                Layout.preferredWidth: 58
            }
            AnswerField {
                id: nameFeld
                Layout.fillWidth: true
                implicitHeight: 44
                font.pixelSize: Theme.schriftM
                horizontalAlignment: TextInput.AlignLeft
                leftPadding: Theme.abstandS
                placeholderText: "z.B. Unité 4"
            }
        }

        // -- Normale Karte ----------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 84
            radius: Theme.radiusMittel
            color: Theme.surface
            border.color: Theme.border
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.abstandS
                spacing: 4
                Text {
                    text: "Karte hinzufügen"
                    color: Theme.textSecondary
                    font.pixelSize: Theme.schriftXs
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.abstandXs
                    AnswerField {
                        id: frageFeld
                        Layout.fillWidth: true
                        implicitHeight: 42
                        font.pixelSize: Theme.schriftS
                        horizontalAlignment: TextInput.AlignLeft
                        leftPadding: Theme.abstandS
                        placeholderText: "Frage"
                        onAccepted: antwortFeld.forceActiveFocus()
                    }
                    AnswerField {
                        id: antwortFeld
                        Layout.fillWidth: true
                        implicitHeight: 42
                        font.pixelSize: Theme.schriftS
                        horizontalAlignment: TextInput.AlignLeft
                        leftPadding: Theme.abstandS
                        placeholderText: "Antwort"
                        onAccepted: dlg.normaleKarteHinzufuegen()
                    }
                    PrimaryButton {
                        text: "+"
                        implicitWidth: 46
                        implicitHeight: 42
                        onClicked: dlg.normaleKarteHinzufuegen()
                    }
                }
            }
        }

        // -- Drei-Formen-Paket ------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 84
            radius: Theme.radiusMittel
            color: Theme.surface
            border.color: Theme.border
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.abstandS
                spacing: 4
                Text {
                    text: "Drei Formen (erzeugt 3 Karten) — mehrwortige Formen wie „had to“ sind erlaubt"
                    color: Theme.textSecondary
                    font.pixelSize: Theme.schriftXs
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.abstandXs
                    AnswerField {
                        id: form1
                        Layout.fillWidth: true; implicitHeight: 42
                        font.pixelSize: Theme.schriftS
                        placeholderText: "go"
                        onAccepted: form2.forceActiveFocus()
                    }
                    AnswerField {
                        id: form2
                        Layout.fillWidth: true; implicitHeight: 42
                        font.pixelSize: Theme.schriftS
                        placeholderText: "went"
                        onAccepted: form3.forceActiveFocus()
                    }
                    AnswerField {
                        id: form3
                        Layout.fillWidth: true; implicitHeight: 42
                        font.pixelSize: Theme.schriftS
                        placeholderText: "gone"
                        onAccepted: dlg.tripleHinzufuegen()
                    }
                    PrimaryButton {
                        text: "+ 3"
                        implicitWidth: 56
                        implicitHeight: 42
                        onClicked: dlg.tripleHinzufuegen()
                    }
                }
            }
        }

        // -- Kartenliste ------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: karten.count + (karten.count === 1 ? " Karte" : " Karten")
                color: Theme.textSecondary
                font.pixelSize: Theme.schriftS
            }
            PrimaryButton {
                text: "Aus Text einfügen …"
                sekundaer: true
                implicitWidth: 160
                implicitHeight: 30
                onClicked: textImport.oeffnen()
            }
        }

        ListView {
            id: kartenListe
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: karten
            spacing: 3
            ScrollBar.vertical: ScrollBar {}

            delegate: Rectangle {
                required property int index
                required property string q
                required property string a
                width: kartenListe.width - 12
                height: 36
                radius: Theme.radiusKlein
                color: zeile.containsMouse ? Theme.surfaceElevated : Theme.surface

                MouseArea { id: zeile; anchors.fill: parent; hoverEnabled: true }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.abstandS
                    anchors.rightMargin: 4
                    spacing: Theme.abstandXs
                    Text {
                        Layout.preferredWidth: parent.width * 0.45
                        text: parent.parent.q
                        color: Theme.textPrimary
                        font.pixelSize: Theme.schriftS
                        elide: Text.ElideRight
                    }
                    Text {
                        text: "→"; color: Theme.textDisabled; font.pixelSize: Theme.schriftS
                    }
                    Text {
                        Layout.fillWidth: true
                        text: parent.parent.a
                        color: Theme.primary
                        font.pixelSize: Theme.schriftS
                        font.bold: true
                        elide: Text.ElideRight
                    }
                    ToolButton {
                        implicitWidth: 28; implicitHeight: 28
                        onClicked: karten.remove(parent.parent.index)
                        background: Rectangle {
                            radius: Theme.radiusKlein
                            color: parent.hovered ? Theme.error : "transparent"
                        }
                        contentItem: Text {
                            text: "✕"
                            color: parent.hovered ? "#ffffff" : Theme.textSecondary
                            font.pixelSize: 13
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: karten.count === 0
                text: "Noch keine Karten"
                color: Theme.textDisabled
                font.pixelSize: Theme.schriftS
            }
        }
    }

    Dialog {
        id: textImport
        anchors.centerIn: Overlay.overlay
        modal: true
        width: 560
        height: 480
        title: "Karten aus Text einfügen"
        closePolicy: Popup.CloseOnEscape

        function oeffnen() {
            quelle.text = ""
            open()
            quelle.forceActiveFocus()
        }

        readonly property var vorschau: sets.textVorschau(quelle.text)

        // Das Erkannte landet im Einfügefeld, nicht direkt im Lernset - so
        // sieht der Nutzer jede Zeile in der Vorschau, bevor etwas
        // gespeichert wird.
        Connections {
            target: sets
            function onVokabelnErkannt(text, zusammenfassung) {
                if (!textImport.visible) return
                quelle.text = text
                quelle.forceActiveFocus()
            }
        }

        FileDialog {
            id: dokumentDialog
            title: "PDF oder Textdatei wählen"
            nameFilters: ["Dokumente (*.pdf *.txt *.csv *.tsv *.md)", "Alle Dateien (*)"]
            onAccepted: sets.ausDokument(selectedFile)
        }

        background: Rectangle {
            color: Theme.background
            radius: Theme.radiusGross
            border.color: Theme.border
            border.width: 1
        }
        header: Text {
            text: textImport.title
            color: Theme.textPrimary
            font.pixelSize: Theme.schriftL
            font.bold: true
            padding: Theme.abstandM
        }

        contentItem: ColumnLayout {
            spacing: Theme.abstandS

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.abstandS

                PrimaryButton {
                    implicitHeight: 32
                    Layout.preferredWidth: 200
                    enabled: sets.kiVerfuegbar && !sets.erkennungLaeuft
                    text: sets.erkennungLaeuft ? "Wird gelesen …" : "Aus PDF oder Datei …"
                    onClicked: dokumentDialog.open()
                }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: sets.erkennungLaeuft
                          ? "Die Seite wird gelesen, das dauert einen Moment."
                          : sets.kiVerfuegbar
                            ? "Buchseite als PDF wählen — die Vokabeln landen unten zum Prüfen."
                            : "Für den PDF-Import ist kein Zugang eingerichtet."
                    color: Theme.textSecondary
                    font.pixelSize: Theme.schriftXs
                }
            }

            Text {
                Layout.fillWidth: true
                text: "Eine Zeile je Karte. Zwei Felder ergeben eine Karte, drei Felder "
                      + "ein Verbpaket.
Trennzeichen: Tabulator, Semikolon oder Komma."
                color: Theme.textSecondary
                font.pixelSize: Theme.schriftXs
                wrapMode: Text.WordWrap
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                TextArea {
                    id: quelle
                    color: Theme.textPrimary
                    placeholderTextColor: Theme.textDisabled
                    placeholderText: "être;sein
avoir;haben
go;went;gone"
                    font.pixelSize: Theme.schriftS
                    selectByMouse: true
                    wrapMode: TextArea.NoWrap
                    background: Rectangle {
                        color: Theme.surface
                        radius: Theme.radiusMittel
                        border.width: quelle.activeFocus ? 2 : 1
                        border.color: quelle.activeFocus ? Theme.primary : Theme.border
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: vorschauSpalte.implicitHeight + 2 * Theme.abstandS
                radius: Theme.radiusMittel
                color: Theme.surface
                border.width: 1
                border.color: textImport.vorschau.probleme.length > 0
                              ? Theme.warning : Theme.border

                ColumnLayout {
                    id: vorschauSpalte
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.abstandS
                    spacing: 2

                    Text {
                        Layout.fillWidth: true
                        text: quelle.text.trim() === ""
                              ? "Vorschau erscheint beim Tippen"
                              : textImport.vorschau.zusammenfassung
                        color: textImport.vorschau.ok ? Theme.success : Theme.textSecondary
                        font.pixelSize: Theme.schriftS
                        font.bold: textImport.vorschau.ok
                    }
                    Repeater {
                        model: textImport.vorschau.probleme
                        delegate: Text {
                            required property var modelData
                            Layout.fillWidth: true
                            text: "Zeile " + modelData.zeile + ": " + modelData.grund
                                  + "  —  " + modelData.text
                            color: Theme.warning
                            font.pixelSize: Theme.schriftXs
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        footer: RowLayout {
            spacing: Theme.abstandS
            Item { Layout.fillWidth: true }
            PrimaryButton {
                text: "Abbrechen"
                sekundaer: true
                implicitWidth: 130
                onClicked: textImport.close()
            }
            PrimaryButton {
                text: "Übernehmen"
                implicitWidth: 150
                enabled: textImport.vorschau.ok
                onClicked: {
                    var neu = sets.textKarten(quelle.text)
                    for (var i = 0; i < neu.length; i++)
                        karten.append({ q: neu[i].q, a: neu[i].a })
                    textImport.close()
                    kartenListe.positionViewAtEnd()
                }
            }
            Item { width: Theme.abstandM }
        }
    }

    footer: RowLayout {
        spacing: Theme.abstandS
        Item { Layout.fillWidth: true }
        PrimaryButton {
            text: "Abbrechen"
            sekundaer: true
            implicitWidth: 130
            onClicked: dlg.close()
        }
        PrimaryButton {
            text: "Speichern"
            implicitWidth: 150
            enabled: karten.count > 0 && nameFeld.text.trim() !== ""
            onClicked: dlg.speichern()
        }
        Item { width: Theme.abstandM }
    }
}
