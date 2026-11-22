import QtQuick
Image {
    id: root
    property string name: "note"
    property color color: Theme.muted
    sourceSize: Qt.size(Theme.iconSize * Screen.devicePixelRatio, Theme.iconSize * Screen.devicePixelRatio)
    width: Theme.iconSize; height: Theme.iconSize
    fillMode: Image.PreserveAspectFit
    property var paths: ({
        "microphone": '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
        "stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
        "history": '<path d="M3 11a9 9 0 1 1 2.6 7.4M3 4v7h7M12 7v5l3 2"/>',
        "settings": '<path d="M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6"/>',
        "pin": '<path d="M12 17v5M9 10V2h6v8M6 3h12l-1 7H7L6 3Z"/>',
        "exit": '<path d="M12 2v10M6.3 5.3a9 9 0 1 0 11.4 0"/>',
        "move": '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z M8 13h8m-3-3 3 3-3 3"/>',
        "note": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h6"/>',
        "folder": '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
        "folder-plus": '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z M9 13h6m-3-3v6"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
        "zoom-in": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5M7.5 10.5h6M10.5 7.5v6"/>',
        "zoom-out": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5M7.5 10.5h6"/>',
        "edit": '<path d="m15 5 4 4M4 20l5-1L20 8a3 3 0 0 0-4-4L5 15Z"/>',
        "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12l4 4v12a2 2 0 0 1-2 2Z M7 3v6h9V3M7 21v-8h10v8"/>',
        "undo": '<path d="M9 7 4 12l5 5M5 12h9a6 6 0 0 1 6 6"/>',
        "trash": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
        "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
        "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5"/>',
        "moon": '<path d="M21 13A9 9 0 0 1 11 3a9 9 0 1 0 10 10Z"/>',
        "chevron": '<path d="m9 5 7 7-7 7"/>',
        "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
        "sidebar": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/>',
        "columns": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M14 3v18"/>',
        "bold": '<path d="M6 4h7a4 4 0 0 1 0 8H6V4Zm0 8h8a4 4 0 0 1 0 8H6Z"/>',
        "italic": '<path d="M10 4h9M5 20h9M15 4 9 20"/>',
        "heading": '<path d="M5 4v16M16 4v16M5 12h11"/>',
        "list": '<path d="M9 6h12M9 12h12M9 18h12M3 6h1M3 12h1M3 18h1"/>',
        "link": '<path d="m10 13 4-4M8 15l-2 2a3 3 0 0 1-4-4l5-5a3 3 0 0 1 4 0M16 9l2-2a3 3 0 0 1 4 4l-5 5a3 3 0 0 1-4 0"/>',
        "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m3 17 5-5 4 4 3-3 6 6"/>',
        "table": '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M9 4v16M15 4v16"/>',
        "code": '<path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18"/>',
        "quote": '<path d="M4 5h6v7H4Zm10 0h6v7h-6ZM10 12c0 5-3 7-6 7M20 12c0 5-3 7-6 7"/>'
    })
    source: "data:image/svg+xml," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + (paths[name] || paths.note) + '</svg>')
}
