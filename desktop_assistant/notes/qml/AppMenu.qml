import QtQuick
import QtQuick.Controls
import "../../ui/components"
Menu {
    id: menu
    property string targetPath: ""
    property bool folder: false
    width: 236
    padding: 5
    delegate: MenuEntry {
        iconName: action ? action.icon.name : ""
        danger: iconName === "trash"
    }
    background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
    Action { text: "Новая заметка"; icon.name: "note"; onTriggered: notesBridge.create(menu.folder ? menu.targetPath : menu.targetPath.substring(0, Math.max(0, menu.targetPath.lastIndexOf('/'))), false) }
    Action { text: "Новая папка"; icon.name: "folder-plus"; onTriggered: notesBridge.create(menu.folder ? menu.targetPath : menu.targetPath.substring(0, Math.max(0, menu.targetPath.lastIndexOf('/'))), true) }
    MenuDivider {}
    Action { text: "Переименовать"; icon.name: "edit"; enabled: menu.targetPath !== ""; onTriggered: notesBridge.rename(menu.targetPath) }
    Action { text: "Переместить…"; icon.name: "move"; enabled: menu.targetPath !== ""; onTriggered: notesBridge.move(menu.targetPath) }
    Action { text: "Удалить…"; icon.name: "trash"; enabled: menu.targetPath !== ""; onTriggered: notesBridge.delete(menu.targetPath) }
}
