import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../ui/components" as Ui

Rectangle {
    id: workspace
    color: Ui.Theme.background
    implicitWidth: 1180; implicitHeight: 740
    function applyTheme() {
        Ui.Theme.dark = notesBridge.dark
        notesBridge.setPreviewStyle(Ui.Theme.family, Ui.Theme.documentFont, Ui.Theme.accent)
        notesBridge.setDialogPalette(Ui.Theme.background, Ui.Theme.surface, Ui.Theme.text, Ui.Theme.accent, Ui.Theme.muted)
    }
    Component.onCompleted: applyTheme()
    Connections {
        target: notesBridge
        function onThemeChanged() {
            var position = editor.cursorPosition
            workspace.applyTheme()
            if (notesBridge.currentPath !== "") {
                editor.text = notesBridge.previewHtml
                editor.cursorPosition = Math.min(position, editor.length)
                editor.deselect()
            }
        }
        function onDocumentChanged() {
            editor.resetUndo()
            editor.text = notesBridge.previewHtml
            editor.cursorPosition = 0
            editor.deselect()
        }
    }
    Shortcut { sequences: [StandardKey.Save]; onActivated: notesBridge.save() }
    Shortcut { sequences: [StandardKey.New]; onActivated: notesBridge.createHere(false) }
    Shortcut { sequence: "Ctrl+Shift+N"; onActivated: notesBridge.createHere(true) }
    Shortcut { sequences: [StandardKey.Find]; onActivated: search.forceActiveFocus() }
    Shortcut { sequence: "Ctrl+Shift+B"; onActivated: notesBridge.toggleLibrary() }
    Shortcut { sequence: "Ctrl+Shift+L"; onActivated: notesBridge.toggleNoteList() }
    Shortcut { sequence: "Ctrl+0"; enabled: notesBridge.currentPath !== ""; onActivated: notesBridge.zoomPreview(0) }

    SplitView {
        id: split
        anchors.fill: parent
        orientation: Qt.Horizontal
        handle: Rectangle {
            implicitWidth: 5
            color: "transparent"
            Rectangle { anchors.centerIn: parent; width: 1; height: parent.height; color: SplitHandle.hovered || SplitHandle.pressed ? Ui.Theme.accent : Ui.Theme.border }
        }
        Ui.Panel {
            visible: notesBridge.libraryVisible
            SplitView.preferredWidth: 236; SplitView.minimumWidth: 180; SplitView.maximumWidth: 420
            color: Ui.Theme.sidebar
            ColumnLayout {
                anchors.fill: parent; spacing: 0
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: Ui.Theme.barHeight
                    Layout.leftMargin: Ui.Theme.panelPadding; Layout.rightMargin: 8; spacing: 2
                    Text { text: "Библиотека"; color: Ui.Theme.text; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.headingFont; font.weight: Font.DemiBold; Layout.fillWidth: true }
                    Ui.ActionButton { iconName: "folder-plus"; hint: "Новая папка · Ctrl+Shift+N"; onClicked: notesBridge.createHere(true) }
                    Ui.ActionButton { iconName: "plus"; hint: "Новая заметка · Ctrl+N"; onClicked: notesBridge.createHere(false) }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Ui.Theme.border }
                FileTree { Layout.fillWidth: true; Layout.fillHeight: true; Layout.topMargin: 8 }
                Rectangle { Layout.fillWidth: true; height: 1; color: Ui.Theme.border }
                RowLayout {
                    Layout.fillWidth: true; Layout.margins: 8; spacing: 2
                    Ui.ActionButton { objectName: "historyAction"; iconName: "history"; hint: "История распознавания"; onClicked: notesBridge.historyRequested() }
                    Ui.ActionButton { objectName: "settingsAction"; iconName: "settings"; hint: "Настройки"; onClicked: notesBridge.settingsRequested() }
                    Item { Layout.fillWidth: true }
                    Ui.ActionButton { iconName: Ui.Theme.dark ? "sun" : "moon"; hint: Ui.Theme.dark ? "Светлая тема" : "Тёмная тема"; onClicked: notesBridge.toggleTheme() }
                    Ui.ActionButton { objectName: "quitAction"; iconName: "exit"; hint: "Выход"; danger: true; onClicked: notesBridge.confirmQuit() }
                }
            }
        }
        Ui.Panel {
            visible: notesBridge.listVisible
            SplitView.preferredWidth: 290; SplitView.minimumWidth: 220; SplitView.maximumWidth: 460
            ColumnLayout {
                anchors.fill: parent; spacing: 0
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: Ui.Theme.barHeight
                    Layout.leftMargin: 16; Layout.rightMargin: 16
                    Text { text: notesBridge.folderTitle; elide: Text.ElideRight; Layout.fillWidth: true; color: Ui.Theme.text; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.headingFont; font.weight: Font.DemiBold }
                    Text { text: notesBridge.notes.length; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.fontSize }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Ui.Theme.border }
                Ui.Input {
                    id: search
                    objectName: "notesSearch"
                    Layout.fillWidth: true; Layout.margins: 12
                    placeholderText: "Поиск по заметкам"; leftPadding: 34
                    Accessible.name: placeholderText
                    onTextChanged: notesBridge.search(text)
                    Ui.OutlineIcon { name: "search"; x: 10; anchors.verticalCenter: parent.verticalCenter; width: 16; height: 16 }
                }
                ListView {
                    id: notesList
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true; model: notesBridge.notes
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {}
                    delegate: ItemDelegate {
                        id: noteRow
                        required property var modelData
                        width: notesList.width; height: 88
                        Accessible.name: modelData.title
                        onClicked: notesBridge.openNote(modelData.path)
                        background: Rectangle {
                            color: notesBridge.currentPath === noteRow.modelData.path ? Ui.Theme.selected : noteRow.hovered ? Ui.Theme.hover : "transparent"
                            Rectangle { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; anchors.leftMargin: 16; anchors.rightMargin: 16; height: 1; color: Ui.Theme.border }
                            Rectangle { width: 2; height: parent.height; color: Ui.Theme.accent; visible: notesBridge.currentPath === noteRow.modelData.path }
                        }
                        contentItem: Column {
                            spacing: 5
                            leftPadding: 10; rightPadding: 10; topPadding: 5
                            Text { width: parent.width - 20; text: noteRow.modelData.title; elide: Text.ElideRight; color: Ui.Theme.text; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.fontSize; font.weight: Font.DemiBold }
                            Text { width: parent.width - 20; text: noteRow.modelData.excerpt; elide: Text.ElideRight; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.fontSize }
                            Text { text: noteRow.modelData.date; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont }
                        }
                        TapHandler {
                            acceptedButtons: Qt.RightButton
                            onTapped: (point) => { listMenu.targetPath = noteRow.modelData.path; listMenu.folder = false; listMenu.popup(noteRow, point.position.x, point.position.y) }
                        }
                    }
                    Text {
                        anchors.centerIn: parent; width: parent.width - 32
                        visible: notesList.count === 0
                        text: search.text ? "Ничего не найдено\nПопробуйте другой запрос" : "В этой папке пока нет заметок\nСоздайте первую с помощью +"
                        wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; lineHeight: 1.5
                        color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.fontSize
                    }
                    AppMenu { id: listMenu }
                }
            }
        }
        Ui.Panel {
            SplitView.fillWidth: true; SplitView.minimumWidth: 400
            ColumnLayout {
                anchors.fill: parent; spacing: 0
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: Ui.Theme.barHeight
                    Layout.leftMargin: 20; Layout.rightMargin: 12; spacing: 3
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 1
                        Text { text: notesBridge.title; elide: Text.ElideRight; Layout.fillWidth: true; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.headingFont; font.weight: Font.DemiBold; color: Ui.Theme.text }
                        Text { visible: notesBridge.currentPath !== ""; text: notesBridge.breadcrumbs; elide: Text.ElideMiddle; Layout.fillWidth: true; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont; color: Ui.Theme.muted }
                    }
                    Ui.ActionButton { iconName: "sidebar"; hint: (notesBridge.libraryVisible ? "Скрыть" : "Показать") + " библиотеку · Ctrl+Shift+B"; checked: notesBridge.libraryVisible; onClicked: notesBridge.toggleLibrary() }
                    Ui.ActionButton { iconName: "columns"; hint: (notesBridge.listVisible ? "Скрыть" : "Показать") + " список заметок · Ctrl+Shift+L"; checked: notesBridge.listVisible; onClicked: notesBridge.toggleNoteList() }
                    Rectangle { width: 1; height: 20; color: Ui.Theme.border; Layout.leftMargin: 5; Layout.rightMargin: 5 }
                    Ui.ActionButton { iconName: "save"; hint: "Сохранить · Ctrl+S"; enabled: notesBridge.dirty; onClicked: notesBridge.save() }
                    Ui.ActionButton { iconName: "more"; hint: "Действия с заметкой"; enabled: notesBridge.currentPath !== ""; onClicked: { documentMenu.targetPath = notesBridge.currentPath; documentMenu.folder = false; documentMenu.popup() } AppMenu { id: documentMenu } }
                    Ui.ActionButton { iconName: "trash"; hint: "Удалить заметку"; enabled: notesBridge.currentPath !== ""; onClicked: notesBridge.delete(notesBridge.currentPath) }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Ui.Theme.border }
                RowLayout {
                    visible: notesBridge.currentPath !== ""
                    Layout.fillWidth: true; Layout.preferredHeight: 44; Layout.leftMargin: 20; Layout.rightMargin: 20
                    spacing: 3
                    Ui.ActionButton { iconName: "undo"; hint: "Отменить · Ctrl+Z"; enabled: notesBridge.canUndo; onClicked: editor.undoEdit() }
                    Rectangle { width: 1; height: 18; color: Ui.Theme.border; Layout.rightMargin: 3 }
                    Ui.ActionButton { iconName: "heading"; hint: "Заголовок"; onClicked: editor.format("heading") }
                    Ui.ActionButton { iconName: "bold"; hint: "Жирный · Ctrl+B"; onClicked: editor.format("bold") }
                    Ui.ActionButton { iconName: "italic"; hint: "Курсив · Ctrl+I"; onClicked: editor.format("italic") }
                    Rectangle { width: 1; height: 18; color: Ui.Theme.border; Layout.leftMargin: 6; Layout.rightMargin: 6 }
                    Ui.ActionButton { iconName: "list"; hint: "Маркированный список"; onClicked: editor.format("list") }
                    Ui.ActionButton { iconName: "quote"; hint: "Цитата"; onClicked: editor.format("quote") }
                    Ui.ActionButton { iconName: "link"; hint: "Ссылка: выделите URL"; onClicked: editor.format("link") }
                    Ui.ActionButton { iconName: "image"; hint: "Вставить изображение"; onClicked: editor.insertImage() }
                    Ui.ActionButton { iconName: "table"; hint: "Вставить таблицу"; onClicked: editor.format("table") }
                    Ui.ActionButton { iconName: "code"; hint: "Код"; onClicked: editor.format("code") }
                    Item { Layout.fillWidth: true }
                    Text { text: "Редактируется здесь"; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Ui.Theme.border }
                Item {
                    id: documentArea
                    Layout.fillWidth: true; Layout.fillHeight: true
                    ScrollView {
                        id: editScroll
                        contentWidth: availableWidth
                        anchors.fill: parent
                        visible: notesBridge.currentPath !== ""
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        TextArea {
                            id: editor
                            objectName: "markdownEditor"
                            width: editScroll.availableWidth
                            textFormat: TextEdit.RichText
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true; persistentSelection: true
                            color: Ui.Theme.text; selectionColor: Ui.Theme.accent; selectedTextColor: Ui.Theme.background
                            font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.documentFont
                            padding: Ui.Theme.documentPadding
                            background: null
                            placeholderText: "Начните писать…"
                            Accessible.name: "Интерактивный редактор Markdown"
                            onTextChanged: notesBridge.updateRichContent(text)
                            function resetUndo() {}
                            function replaceForCommand(result) {
                                text = result.html
                                cursorPosition = result.position
                                notesBridge.updateRichContent(text)
                            }
                            function format(action) {
                                var result = notesBridge.formatRichContent(text, selectionStart, selectionEnd, action)
                                replaceForCommand(result)
                                forceActiveFocus()
                            }
                            function formatAt(action, position) {
                                var result = notesBridge.formatRichContent(text, position, position, action)
                                replaceForCommand(result)
                                forceActiveFocus()
                            }
                            function insertImage() {
                                var result = notesBridge.insertRichImage(text, cursorPosition)
                                replaceForCommand(result)
                                forceActiveFocus()
                            }
                            function undoEdit() {
                                notesBridge.undoContent()
                                forceActiveFocus()
                            }
                            Shortcut { sequence: "Ctrl+B"; onActivated: editor.format("bold") }
                            Shortcut { sequence: "Ctrl+I"; onActivated: editor.format("italic") }
                            Shortcut { sequence: "Ctrl+Z"; onActivated: editor.undoEdit() }

                            TapHandler {
                                onTapped: (point) => {
                                    var position = editor.positionAt(point.position.x, point.position.y)
                                    if (position >= 0 && notesBridge.cursorInTable(editor.text, position)) {
                                        tableActions.documentPosition = position
                                        var location = editor.mapToItem(documentArea, point.position.x, point.position.y)
                                        tableActions.x = Math.max(8, Math.min(location.x, documentArea.width - tableActions.width - 8))
                                        tableActions.y = Math.max(8, location.y - tableActions.height - 10)
                                        tableActions.visible = true
                                    } else {
                                        tableActions.visible = false
                                    }
                                }
                            }
                        }
                    }
                    // This must be a sibling of TextArea. If it is a child,
                    // TextArea consumes pointer presses before its buttons do.
                    Rectangle {
                        id: tableActions
                        visible: false
                        z: 10
                        property int documentPosition: 0
                        width: actionsRow.width + 16; height: 38; radius: 7
                        color: Ui.Theme.surface
                        border.color: Ui.Theme.border
                        Row {
                            id: actionsRow
                            anchors.centerIn: parent; spacing: 14
                            Repeater {
                                model: [
                                    { label: "+ строка", action: "add-row", danger: false },
                                    { label: "+ столбец", action: "add-column", danger: false },
                                    { label: "− строка", action: "delete-row", danger: true },
                                    { label: "− столбец", action: "delete-column", danger: true },
                                    { label: "удалить таблицу", action: "delete-table", danger: true }
                                ]
                                delegate: Text {
                                    required property var modelData
                                    text: modelData.label
                                    color: modelData.danger ? "#e58b63" : Ui.Theme.text
                                    font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            editor.formatAt(parent.modelData.action, tableActions.documentPosition)
                                            if (parent.modelData.action === "delete-table") tableActions.visible = false
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Column {
                        anchors.centerIn: parent; spacing: 14
                        visible: notesBridge.currentPath === ""
                        Ui.OutlineIcon { anchors.horizontalCenter: parent.horizontalCenter; name: "note"; width: 32; height: 32; color: Ui.Theme.muted }
                        Text { text: "Место для ваших мыслей"; anchors.horizontalCenter: parent.horizontalCenter; color: Ui.Theme.text; font.family: Ui.Theme.family; font.pixelSize: 18 }
                        Text { text: "Выберите заметку или создайте новую · Ctrl+N"; anchors.horizontalCenter: parent.horizontalCenter; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.fontSize }
                    }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Ui.Theme.border }
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 32; Layout.leftMargin: 20; Layout.rightMargin: 20
                    Text { text: !notesBridge.currentPath ? "Нет открытой заметки" : notesBridge.dirty ? "Есть несохранённые изменения" : "Сохранено"; color: notesBridge.dirty ? Ui.Theme.accent : Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont; Layout.fillWidth: true; elide: Text.ElideRight }
                    Text { text: notesBridge.currentPath ? notesBridge.statistics : "Markdown"; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont }
                    Row {
                        visible: notesBridge.currentPath !== "" && !notesBridge.editing
                        spacing: 1
                        Ui.ActionButton { width: 28; height: 28; iconName: "zoom-out"; hint: "Уменьшить масштаб · Ctrl+колесо вниз"; enabled: notesBridge.previewZoom > 60; onClicked: notesBridge.zoomPreview(-1) }
                        Text {
                            width: 46; height: 28; text: notesBridge.previewZoom + "%"
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                            color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont
                            ToolTip.visible: zoomReset.containsMouse; ToolTip.text: "Сбросить масштаб · Ctrl+0"
                            MouseArea { id: zoomReset; anchors.fill: parent; hoverEnabled: true; onClicked: notesBridge.zoomPreview(0) }
                        }
                        Ui.ActionButton { width: 28; height: 28; iconName: "zoom-in"; hint: "Увеличить масштаб · Ctrl+колесо вверх"; enabled: notesBridge.previewZoom < 200; onClicked: notesBridge.zoomPreview(1) }
                    }
                }
            }
        }
    }
}
