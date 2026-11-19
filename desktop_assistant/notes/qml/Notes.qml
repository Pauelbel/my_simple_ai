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
        function onThemeChanged() { workspace.applyTheme() }
        function onDocumentChanged() { editor.text = notesBridge.content }
    }
    Shortcut { sequences: [StandardKey.Save]; onActivated: notesBridge.save() }
    Shortcut { sequences: [StandardKey.New]; onActivated: notesBridge.createHere(false) }
    Shortcut { sequence: "Ctrl+Shift+N"; onActivated: notesBridge.createHere(true) }
    Shortcut { sequences: [StandardKey.Find]; onActivated: search.forceActiveFocus() }
    Shortcut { sequence: "Ctrl+E"; enabled: notesBridge.currentPath !== ""; onActivated: notesBridge.setEditing(!notesBridge.editing) }
    Shortcut { sequence: "Ctrl+Shift+B"; onActivated: notesBridge.toggleLibrary() }
    Shortcut { sequence: "Ctrl+Shift+L"; onActivated: notesBridge.toggleNoteList() }
    Shortcut { sequence: "Ctrl+0"; enabled: !notesBridge.editing; onActivated: notesBridge.zoomPreview(0) }

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
                    Layout.fillWidth: true; Layout.margins: 8
                    Ui.OutlineIcon { name: "folder" }
                    Text { text: "Локальные заметки"; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont; Layout.fillWidth: true }
                    Ui.ActionButton { iconName: Ui.Theme.dark ? "sun" : "moon"; hint: Ui.Theme.dark ? "Светлая тема" : "Тёмная тема"; onClicked: notesBridge.toggleTheme() }
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
                    Text { text: notesBridge.title; elide: Text.ElideRight; Layout.fillWidth: true; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.headingFont; font.weight: Font.DemiBold; color: Ui.Theme.text }
                    Ui.ActionButton { iconName: "sidebar"; hint: (notesBridge.libraryVisible ? "Скрыть" : "Показать") + " библиотеку · Ctrl+Shift+B"; checked: notesBridge.libraryVisible; onClicked: notesBridge.toggleLibrary() }
                    Ui.ActionButton { iconName: "columns"; hint: (notesBridge.listVisible ? "Скрыть" : "Показать") + " список заметок · Ctrl+Shift+L"; checked: notesBridge.listVisible; onClicked: notesBridge.toggleNoteList() }
                    Rectangle { width: 1; height: 20; color: Ui.Theme.border; Layout.leftMargin: 5; Layout.rightMargin: 5 }
                    Ui.ActionButton { iconName: "save"; hint: "Сохранить · Ctrl+S"; enabled: notesBridge.dirty; onClicked: notesBridge.save() }
                    Rectangle { width: 1; height: 20; color: Ui.Theme.border; Layout.leftMargin: 5; Layout.rightMargin: 5 }
                    Ui.ActionButton { iconName: "eye"; hint: "Просмотр · Ctrl+E"; checked: !notesBridge.editing; enabled: notesBridge.currentPath !== ""; onClicked: notesBridge.setEditing(false) }
                    Ui.ActionButton { iconName: "edit"; hint: "Редактировать · Ctrl+E"; checked: notesBridge.editing; enabled: notesBridge.currentPath !== ""; onClicked: { notesBridge.setEditing(true); editor.forceActiveFocus() } }
                    Ui.ActionButton { iconName: "more"; hint: "Действия с заметкой"; enabled: notesBridge.currentPath !== ""; onClicked: { documentMenu.targetPath = notesBridge.currentPath; documentMenu.folder = false; documentMenu.popup() } AppMenu { id: documentMenu } }
                    Ui.ActionButton { iconName: "trash"; hint: "Удалить заметку"; enabled: notesBridge.currentPath !== ""; onClicked: notesBridge.delete(notesBridge.currentPath) }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Ui.Theme.border }
                RowLayout {
                    visible: notesBridge.editing && notesBridge.currentPath !== ""
                    Layout.fillWidth: true; Layout.preferredHeight: 44; Layout.leftMargin: 20; Layout.rightMargin: 20
                    spacing: 3
                    Ui.ActionButton { iconName: "heading"; hint: "Заголовок"; onClicked: editor.prefix("## ") }
                    Ui.ActionButton { iconName: "bold"; hint: "Жирный · Ctrl+B"; onClicked: editor.wrap("**", "**", "текст") }
                    Ui.ActionButton { iconName: "italic"; hint: "Курсив · Ctrl+I"; onClicked: editor.wrap("*", "*", "текст") }
                    Rectangle { width: 1; height: 18; color: Ui.Theme.border; Layout.leftMargin: 6; Layout.rightMargin: 6 }
                    Ui.ActionButton { iconName: "list"; hint: "Маркированный список"; onClicked: editor.prefix("- ") }
                    Ui.ActionButton { iconName: "quote"; hint: "Цитата"; onClicked: editor.prefix("> ") }
                    Ui.ActionButton { iconName: "link"; hint: "Ссылка"; onClicked: editor.wrap("[", "](https://)", "название") }
                    Ui.ActionButton { iconName: "image"; hint: "Вставить изображение"; onClicked: editor.insertBlock(notesBridge.importImage()) }
                    Ui.ActionButton { iconName: "table"; hint: "Вставить таблицу"; onClicked: editor.insertBlock("| Столбец 1 | Столбец 2 |\n| --- | --- |\n| Значение 1 | Значение 2 |") }
                    Ui.ActionButton { iconName: "code"; hint: "Код"; onClicked: editor.wrap("`", "`", "код") }
                    Item { Layout.fillWidth: true }
                    Text { text: "Markdown"; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont }
                }
                Rectangle { visible: notesBridge.editing; Layout.fillWidth: true; height: 1; color: Ui.Theme.border }
                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    ScrollView {
                        id: editScroll
                        contentWidth: availableWidth
                        anchors.fill: parent
                        visible: notesBridge.currentPath !== "" && notesBridge.editing
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        TextArea {
                            id: editor
                            objectName: "markdownEditor"
                            width: editScroll.availableWidth
                            textFormat: TextEdit.PlainText
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true; persistentSelection: true
                            color: Ui.Theme.text; selectionColor: Ui.Theme.accent; selectedTextColor: Ui.Theme.background
                            font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.documentFont
                            padding: Ui.Theme.documentPadding
                            background: null
                            placeholderText: "Начните писать…"
                            Accessible.name: "Редактор Markdown"
                            onTextChanged: notesBridge.updateContent(text)
                            function wrap(before, after, placeholder) {
                                var start = selectionStart, end = selectionEnd
                                var selected = selectedText || placeholder
                                remove(start, end); insert(start, before + selected + after)
                                select(start + before.length, start + before.length + selected.length)
                                forceActiveFocus()
                            }
                            function prefix(mark) {
                                var start = text.lastIndexOf("\n", Math.max(0, selectionStart - 1)) + 1
                                var end = selectionEnd
                                var selected = text.substring(start, end)
                                remove(start, end); insert(start, mark + selected.replace(/\n/g, "\n" + mark))
                                forceActiveFocus()
                            }
                            function insertBlock(markdown) {
                                if (!markdown) return
                                var start = selectionStart
                                var before = start > 0 && text.charAt(start - 1) !== "\n" ? "\n\n" : ""
                                var after = start < text.length && text.charAt(start) !== "\n" ? "\n\n" : "\n"
                                insert(start, before + markdown + after)
                                cursorPosition = start + before.length + markdown.length
                                forceActiveFocus()
                            }
                            Shortcut { sequence: "Ctrl+B"; enabled: notesBridge.editing; onActivated: editor.wrap("**", "**", "текст") }
                            Shortcut { sequence: "Ctrl+I"; enabled: notesBridge.editing; onActivated: editor.wrap("*", "*", "текст") }
                        }
                    }
                    ScrollView {
                        id: previewScroll
                        contentWidth: availableWidth
                        anchors.fill: parent
                        visible: notesBridge.currentPath !== "" && !notesBridge.editing
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        TextArea {
                            id: preview
                            objectName: "markdownPreview"
                            width: previewScroll.availableWidth
                            text: notesBridge.previewHtml
                            textFormat: TextEdit.RichText
                            wrapMode: TextEdit.Wrap
                            readOnly: true; selectByMouse: true
                            color: Ui.Theme.text
                            selectionColor: Ui.Theme.accent; selectedTextColor: Ui.Theme.background
                            font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.documentFont
                            padding: Ui.Theme.documentPadding
                            background: null
                            Accessible.name: "Просмотр Markdown"
                            onLinkActivated: (link) => notesBridge.openLink(link)
                            WheelHandler {
                                acceptedModifiers: Qt.ControlModifier
                                onWheel: (event) => notesBridge.zoomPreview(event.angleDelta.y)
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
                    Text { text: notesBridge.currentPath ? notesBridge.statistics + (!notesBridge.editing ? " · " + notesBridge.previewZoom + "%" : "") : "Markdown"; color: Ui.Theme.muted; font.family: Ui.Theme.family; font.pixelSize: Ui.Theme.smallFont }
                }
            }
        }
    }
}
