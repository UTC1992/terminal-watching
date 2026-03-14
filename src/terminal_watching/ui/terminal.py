import curses
from typing import Optional
from terminal_watching.domain.models import AppState, AppStatus, Tab
from terminal_watching.domain.ports import UIRenderer


class CursesRenderer(UIRenderer):
    """Terminal UI using curses with fixed header and scrollable bottom."""

    def __init__(self):
        self._screen = None
        self._header_win = None
        self._tab_win = None
        self._content_win = None
        self._last_rows = 0
        self._last_cols = 0

    def setup(self) -> None:
        self._screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self._screen.keypad(True)
        self._screen.nodelay(True)
        # Enable mouse wheel support
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        # SGR mouse mode for better wheel detection on macOS
        print('\033[?1000h\033[?1002h\033[?1006h', end='', flush=True)

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)    # ready
            curses.init_pair(2, curses.COLOR_YELLOW, -1)   # starting
            curses.init_pair(3, curses.COLOR_RED, -1)      # error
            curses.init_pair(4, curses.COLOR_CYAN, -1)     # urls
            curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)  # selected tab
            curses.init_pair(6, curses.COLOR_WHITE, -1)    # dim

        self._create_windows()

    def teardown(self) -> None:
        if self._screen:
            print('\033[?1006l\033[?1002l\033[?1000l', end='', flush=True)
            curses.nocbreak()
            self._screen.keypad(False)
            curses.echo()
            curses.endwin()

    def _create_windows(self) -> None:
        rows, cols = self._screen.getmaxyx()
        self._last_rows = rows
        self._last_cols = cols

        header_height = 8
        tab_height = 3
        content_height = max(1, rows - header_height - tab_height)

        self._header_win = curses.newwin(header_height, cols, 0, 0)
        self._tab_win = curses.newwin(tab_height, cols, header_height, 0)
        self._content_win = curses.newwin(content_height, cols, header_height + tab_height, 0)
        self._content_win.scrollok(True)

    def _check_resize(self) -> bool:
        rows, cols = self._screen.getmaxyx()
        if rows != self._last_rows or cols != self._last_cols:
            self._create_windows()
            return True
        return False

    def render(self, state: AppState) -> None:
        try:
            self._check_resize()
            self._draw_header(state)
            self._draw_tabs(state)
            self._draw_content(state)
            curses.doupdate()
        except curses.error:
            pass

    def _draw_header(self, state: AppState) -> None:
        win = self._header_win
        win.erase()
        rows, cols = win.getmaxyx()
        line = '=' * (cols - 1)

        win.addstr(0, 0, line, curses.A_BOLD)
        title = f"{state.project_name} - Dev Server"
        win.addstr(1, 2, title[:cols - 4], curses.A_BOLD)
        win.addstr(2, 0, line, curses.A_BOLD)

        # Status
        status_text = state.status.value
        color = self._status_color(state.status)
        win.addstr(3, 2, "Status: ")
        win.addstr(3, 10, status_text, color | curses.A_BOLD)

        # URL (dynamic port)
        if state.port:
            url = f"http://localhost:{state.port}"
            win.addstr(4, 2, "URL: ")
            win.addstr(4, 7, url, curses.color_pair(4))
        else:
            win.addstr(4, 2, "URL: ", curses.A_DIM)
            win.addstr(4, 7, "N/A", curses.A_DIM)

        # Message
        if state.message:
            msg = state.message[:cols - 4]
            win.addstr(5, 2, msg, curses.A_DIM)

        win.addstr(7, 0, '-' * (cols - 1))

        win.noutrefresh()

    def _draw_tabs(self, state: AppState) -> None:
        win = self._tab_win
        win.erase()
        _, cols = win.getmaxyx()

        x = 2
        for key, tab, label in [('e', Tab.ERRORS, 'ERRORS'),
                                  ('h', Tab.REQUESTS, 'REQUESTS'),
                                  ('l', Tab.LOGS, 'LOGS')]:
            is_active = state.active_tab == tab
            win.addstr(0, x, f"[{key}]", curses.A_DIM)
            x += len(f"[{key}]")

            if is_active:
                win.addstr(0, x, f" {label} ", curses.color_pair(5) | curses.A_BOLD)
            else:
                win.addstr(0, x, f" {label.lower()} ", curses.A_DIM)
            x += len(f" {label} ") + 1

        # Controls
        controls = "| r=restart  q=quit  w=wrap  scroll=UP/DOWN"
        if x + len(controls) + 1 < cols:
            win.addstr(0, x + 1, controls, curses.A_DIM)

        win.addstr(1, 0, '=' * (cols - 1), curses.A_BOLD)

        win.noutrefresh()

    def _draw_content(self, state: AppState) -> None:
        win = self._content_win
        win.erase()
        rows, cols = win.getmaxyx()

        lines = state.get_display_lines(cols)
        total = len(lines)

        # Auto-scroll to bottom if at the end
        max_scroll = max(0, total - rows)
        if state.scroll_offset > max_scroll:
            state.scroll_offset = max_scroll

        start = state.scroll_offset
        visible = lines[start:start + rows]

        for i, line in enumerate(visible):
            if i >= rows - 1:
                break
            display = line.replace('\t', '  ')[:cols - 2]
            color = self._line_color(line, state.active_tab)
            try:
                win.addnstr(i, 0, display, cols - 2, color)
            except curses.error:
                pass

        # Scroll indicator + wrap mode
        wrap_label = "WRAP" if state.wrap_lines else "TRUNCATE"
        if total > rows:
            pct = int((start / max(1, max_scroll)) * 100) if max_scroll > 0 else 100
            indicator = f" [{start + 1}-{min(start + rows, total)}/{total}] {pct}% [{wrap_label}] "
        else:
            indicator = f" [{wrap_label}] "
        try:
            win.addstr(rows - 1, max(0, cols - len(indicator) - 1),
                      indicator, curses.A_DIM)
        except curses.error:
            pass

        win.noutrefresh()

    def get_key(self) -> Optional[str]:
        try:
            ch = self._screen.getch()
            if ch == -1:
                return None
            if ch == curses.KEY_MOUSE:
                try:
                    _, _, _, _, bstate = curses.getmouse()
                    # Wheel up
                    if bstate & curses.BUTTON4_PRESSED:
                        return 'SCROLL_UP'
                    # Wheel down — try multiple constants
                    BUTTON5 = getattr(curses, 'BUTTON5_PRESSED', 2097152)
                    if bstate & BUTTON5:
                        return 'SCROLL_DOWN'
                    # Some terminals report wheel as button 4/5 release
                    if bstate & curses.BUTTON4_RELEASED:
                        return 'SCROLL_UP'
                except curses.error:
                    pass
                return None
            # SGR mouse sequences come as escape sequences
            # Parse them: \033[<btn;x;yM or \033[<btn;x;ym
            if ch == 27:  # ESC
                seq = ''
                while True:
                    c = self._screen.getch()
                    if c == -1:
                        break
                    seq += chr(c)
                    if c in (ord('M'), ord('m'), ord('~')):
                        break
                    if len(seq) > 20:
                        break
                # SGR format: [<btn;x;yM
                if seq.startswith('[<'):
                    parts = seq[2:].rstrip('Mm').split(';')
                    if len(parts) >= 1:
                        btn = int(parts[0])
                        if btn == 64:  # wheel up
                            return 'SCROLL_UP'
                        if btn == 65:  # wheel down
                            return 'SCROLL_DOWN'
                return None
            if ch == curses.KEY_UP:
                return 'UP'
            if ch == curses.KEY_DOWN:
                return 'DOWN'
            if ch == curses.KEY_PPAGE:
                return 'PGUP'
            if ch == curses.KEY_NPAGE:
                return 'PGDN'
            if ch == curses.KEY_RESIZE:
                return 'RESIZE'
            if 0 <= ch <= 255:
                return chr(ch)
            return None
        except (curses.error, ValueError):
            return None

    def _status_color(self, status: AppStatus) -> int:
        if status in (AppStatus.READY,):
            return curses.color_pair(1)
        if status in (AppStatus.STARTING, AppStatus.COMPILING,
                      AppStatus.BOOTING, AppStatus.RESTARTING):
            return curses.color_pair(2)
        if status in (AppStatus.ERROR, AppStatus.STOPPED):
            return curses.color_pair(3)
        return curses.color_pair(0)

    def _line_color(self, line: str, tab: Tab) -> int:
        if tab == Tab.ERRORS:
            if 'ERROR' in line or 'Exception' in line:
                return curses.color_pair(3)
            return curses.color_pair(2)
        if tab == Tab.REQUESTS:
            if ' 2' in line and ('200' in line or '201' in line):
                return curses.color_pair(1)
            if ' 4' in line or ' 5' in line:
                return curses.color_pair(3)
            return curses.color_pair(4)
        return curses.color_pair(0)
