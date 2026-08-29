import QtQuick
import QtQuick.Controls.Basic
import theme

Button {
    id: btn
    property bool sekundaer: false

    implicitWidth: 180
    implicitHeight: 46
    focusPolicy: Qt.StrongFocus

    background: Rectangle {
        radius: Theme.radiusMittel
        color: !btn.enabled ? Theme.border
             : btn.sekundaer ? (btn.hovered ? Theme.surfaceElevated : "transparent")
             : btn.down ? Qt.darker(Theme.primary, 1.25)
             : btn.hovered ? Theme.primaryHover : Theme.primary
        border.width: btn.sekundaer ? 1 : 0
        border.color: btn.activeFocus ? Theme.primary : Theme.border
        Behavior on color { ColorAnimation { duration: Theme.dauerSchnell } }
    }
    contentItem: Text {
        text: btn.text
        color: !btn.enabled ? Theme.textDisabled
             : btn.sekundaer ? Theme.textPrimary : Theme.onPrimary
        font.pixelSize: Theme.schriftM
        font.bold: !btn.sekundaer
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}
