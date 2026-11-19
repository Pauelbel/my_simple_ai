// KWin is the only process that can reliably see global pointer coordinates on KDE Wayland.
// Limit traffic to 120 updates/sec; the assistant interpolates the visual movement itself.
let lastSentAt = 0;

function sendCursorPosition() {
    const now = Date.now();
    if (now - lastSentAt < 8) {
        return;
    }
    lastSentAt = now;
    const point = workspace.cursorPos;
    callDBus(
        "org.desktopassistant.Cursor",
        "/Cursor",
        "local.DesktopAssistant.Cursor",
        "setPosition",
        point.x,
        point.y
    );
}

workspace.cursorPosChanged.connect(sendCursorPosition);
sendCursorPosition();
