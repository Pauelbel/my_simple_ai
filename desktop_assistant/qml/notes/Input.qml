import QtQuick
import QtQuick.Controls
TextField {
    id: field
    implicitHeight: 36
    font.family: Theme.family; font.pixelSize: Theme.fontSize
    color: Theme.text; placeholderTextColor: Theme.muted
    selectionColor: Theme.accent; selectedTextColor: Theme.background
    leftPadding: Theme.panelPadding; rightPadding: Theme.panelPadding
    background: Rectangle {
        radius: Theme.radius; color: Theme.background
        border.color: field.activeFocus ? Theme.accent : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.motion } }
    }
}
