import QtQuick
import QtQuick.Controls
ListView {
    id: tree
    clip: true
    model: notesBridge.treeRows
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}
    delegate: ItemDelegate {
        id: row
        required property var modelData
        required property int index
        width: tree.width; height: Theme.rowHeight
        leftPadding: Theme.treeInset; rightPadding: Theme.treeInset
        text: modelData.name
        Accessible.name: text
        focusPolicy: Qt.StrongFocus
        onClicked: notesBridge.select(modelData.path, modelData.folder)
        Keys.onRightPressed: if (modelData.folder && !modelData.expanded) notesBridge.toggleFolder(modelData.path)
        Keys.onLeftPressed: if (modelData.folder && modelData.expanded) notesBridge.toggleFolder(modelData.path)
        Keys.onReturnPressed: notesBridge.select(modelData.path, modelData.folder)
        Keys.onPressed: (event) => { if (event.key === Qt.Key_F2) { notesBridge.rename(modelData.path); event.accepted = true } }
        background: Rectangle {
            color: notesBridge.selectedPath === row.modelData.path ? Theme.selected : row.hovered ? Theme.hover : "transparent"
            Rectangle { width: 2; height: parent.height; color: Theme.accent; visible: notesBridge.selectedPath === row.modelData.path }
        }
        contentItem: Item {
            Repeater {
                model: row.modelData.guides
                delegate: Rectangle {
                    required property int index
                    required property bool modelData
                    x: Theme.treeInset + (index + 1) * Theme.indent
                    y: -row.topPadding; height: row.height; width: 1
                    color: Theme.border; visible: modelData
                }
            }
            Rectangle {
                visible: row.modelData.depth > 0
                x: Theme.treeInset + row.modelData.depth * Theme.indent
                y: -row.topPadding
                height: row.modelData.last ? row.height / 2 : row.height
                width: 1; color: Theme.border
            }
            Rectangle {
                visible: row.modelData.depth > 0
                x: Theme.treeInset + row.modelData.depth * Theme.indent
                anchors.verticalCenter: parent.verticalCenter
                width: 9; height: 1; color: Theme.border
            }
            ToolButton {
                id: expand
                x: Theme.treeInset + row.modelData.depth * Theme.indent
                anchors.verticalCenter: parent.verticalCenter
                width: Theme.treeToggleWidth; height: Theme.rowHeight
                padding: 3
                visible: row.modelData.folder
                Accessible.name: row.modelData.expanded ? "Свернуть папку" : "Раскрыть папку"
                contentItem: OutlineIcon { name: "chevron"; width: 12; height: 12; rotation: row.modelData.expanded ? 90 : 0; Behavior on rotation { NumberAnimation { duration: Theme.motion } } }
                background: Item {}
                onClicked: notesBridge.toggleFolder(row.modelData.path)
            }
            OutlineIcon {
                id: symbol
                x: Theme.treeInset + row.modelData.depth * Theme.indent + Theme.treeToggleWidth
                anchors.verticalCenter: parent.verticalCenter
                name: row.modelData.folder ? "folder" : "note"
                color: notesBridge.selectedPath === row.modelData.path ? Theme.accent : Theme.muted
                width: 16; height: 16
            }
            Text {
                anchors.left: symbol.right; anchors.leftMargin: 7
                anchors.right: parent.right; anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                text: row.text; elide: Text.ElideRight
                font.family: Theme.family; font.pixelSize: Theme.fontSize
                color: Theme.text
            }
        }
        TapHandler {
            acceptedButtons: Qt.RightButton
            onTapped: (eventPoint) => {
                context.targetPath = row.modelData.path; context.folder = row.modelData.folder
                context.popup(row, eventPoint.position.x, eventPoint.position.y)
            }
        }
    }
    AppMenu { id: context }
}
