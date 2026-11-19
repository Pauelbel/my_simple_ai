import QtQuick
import QtQuick.Controls
ToolButton {
    id: control
    property string iconName: "plus"
    property string hint: ""
    property bool danger: false
    implicitWidth: Theme.buttonSize; implicitHeight: Theme.buttonSize
    focusPolicy: Qt.StrongFocus
    Accessible.name: hint
    ToolTip.visible: hovered && hint.length > 0
    ToolTip.delay: 500
    ToolTip.text: hint
    contentItem: Item {
        OutlineIcon { anchors.centerIn: parent; name: control.iconName; color: !control.enabled ? Theme.disabled : control.danger ? Theme.danger : control.checked ? Theme.accent : Theme.text }
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.down ? Theme.pressed : control.checked ? Theme.selected : control.hovered ? Theme.hover : "transparent"
        border.width: control.activeFocus ? 1 : 0; border.color: Theme.accent
        Behavior on color { ColorAnimation { duration: Theme.motion } }
    }
}
