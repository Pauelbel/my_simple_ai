import QtQuick
import QtQuick.Controls
MenuItem {
    id: control
    property string iconName: ""
    property bool danger: false
    implicitWidth: 268
    implicitHeight: 38
    padding: 0
    font.family: Theme.family
    font.pixelSize: Theme.fontSize
    Accessible.name: text
    indicator: null
    contentItem: Item {
        OutlineIcon {
            id: symbol
            anchors.left: parent.left; anchors.leftMargin: Theme.panelPadding
            anchors.verticalCenter: parent.verticalCenter
            visible: control.iconName !== ""
            name: control.iconName
            color: !control.enabled ? Theme.disabled : control.danger ? Theme.danger : control.checked ? Theme.accent : Theme.muted
        }
        Text {
            anchors.left: parent.left; anchors.leftMargin: control.iconName ? 42 : Theme.panelPadding
            anchors.right: parent.right; anchors.rightMargin: Theme.panelPadding
            anchors.verticalCenter: parent.verticalCenter
            text: control.text
            font: control.font
            elide: Text.ElideRight
            color: !control.enabled ? Theme.disabled : control.danger ? Theme.danger : control.checked ? Theme.accent : Theme.text
        }
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.down ? Theme.pressed : control.highlighted ? Theme.hover : control.checked ? Theme.selected : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.motion } }
    }
}
