// Eingabefeld für Antworten. Enter löst Prüfen aus.
import QtQuick
import QtQuick.Controls.Basic
import theme

TextField {
    id: feld
    property bool falschMarkiert: false

    implicitHeight: 56
    font.pixelSize: Theme.schriftL
    horizontalAlignment: TextInput.AlignHCenter
    color: Theme.textPrimary
    placeholderTextColor: Theme.textDisabled
    selectByMouse: true
    background: Rectangle {
        radius: Theme.radiusMittel
        color: Theme.surfaceElevated
        border.width: feld.activeFocus ? 2 : 1
        border.color: feld.falschMarkiert ? Theme.error
                    : feld.activeFocus ? Theme.primary : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.dauerSchnell } }
    }
}
