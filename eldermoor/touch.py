"""On-screen controls for a touchscreen: a thumb-stick and eight buttons.

A phone has no keyboard, so the twelve logical buttons have to come from
somewhere. They come from here: a round pad under the left thumb that reads
as eight directions, and buttons under the right. Both live in the black
bars either side of the picture, so nothing ever covers the game.

The pad feeds :class:`~eldermoor.input.Input` through its own channel, the
way the keyboard and the gamepad do, which means every button in the game
already works through it and nothing else had to learn about touch.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from eldermoor.input import Input

#: how far from the middle of the pad counts as pushing a direction
DEAD_ZONE = 0.34
#: the pad and the buttons, as a share of the shorter screen edge
PAD_SIZE = 0.46
BUTTON_SIZE = 0.15
SMALL_SIZE = 0.11
#: no control is drawn smaller than this, however cramped the screen
MIN_RADIUS = 16
#: how solid the controls are drawn, untouched and touched
IDLE_ALPHA = 70
HELD_ALPHA = 160


@dataclass(frozen=True)
class Control:
    """One round control: the action it sends, where it is, how big."""

    action: str
    centre: tuple[int, int]
    radius: int
    label: str = ""


class TouchPad:
    """The on-screen controls: their layout, their drawing and their fingers."""

    def __init__(self) -> None:
        self.controls: list[Control] = []
        self.stick: Control | None = None
        #: finger id -> the control it is on ("" while on the stick)
        self.fingers: dict[int, str] = {}
        self.held: set[str] = set()
        #: the directions the thumb is currently pushing
        self.stick_dirs: set[str] = set()
        self.visible = True
        #: the game's own font, so the buttons are lettered rather than blank
        self.font = None
        #: the drawn controls, kept until something about them changes
        self._layer: pygame.Surface | None = None
        self._layer_key: tuple | None = None

    # ----- layout --------------------------------------------------------
    def layout(self, window: tuple[int, int], picture: pygame.Rect) -> None:
        """Place the controls in the space the picture does not use.

        In landscape that is the bars either side; in portrait it is the
        space underneath. Either way the game is never covered.
        """
        width, height = window
        left_bar = picture.left
        right_bar = width - picture.right
        below = height - picture.bottom
        if min(left_bar, right_bar) >= height * 0.22:
            self._beside(picture, width, height)
        elif below >= height * 0.22:
            self._below(picture, width, height)
        else:
            self._over(width, height)
        self._keep_on_screen(width, height)
        self._layer = None

    def _keep_on_screen(self, width: int, height: int) -> None:
        """Last resort: nudge anything hanging off an edge back inside."""
        def fit(control: Control) -> Control:
            x = min(max(control.centre[0], control.radius), width - control.radius)
            y = min(max(control.centre[1], control.radius), height - control.radius)
            if (x, y) == control.centre:
                return control
            return Control(control.action, (x, y), control.radius, control.label)

        self.controls = [fit(c) for c in self.controls]
        if self.stick is not None:
            self.stick = fit(self.stick)

    def _beside(self, picture: pygame.Rect, width: int, height: int) -> None:
        """Landscape: the pad in the left bar, the buttons in the right.

        Everything is sized to the bar it has to fit in, not to the screen:
        a narrow bar on an older phone gets smaller controls rather than
        controls hanging off the edge.
        """
        unit = min(height, width // 3)
        left_bar, right_bar = picture.left, width - picture.right
        pad_r = max(MIN_RADIUS * 2, round(min(unit * PAD_SIZE / 2, left_bar * 0.42)))
        # the face buttons sit in a diamond three and a bit radii wide
        btn_r = max(MIN_RADIUS, round(min(unit * BUTTON_SIZE / 2, right_bar * 0.27)))
        small_r = max(MIN_RADIUS, round(min(unit * SMALL_SIZE / 2, left_bar * 0.3,
                                           right_bar * 0.3)))
        left_mid = picture.left // 2
        right_mid = picture.right + (width - picture.right) // 2
        low = round(height * 0.62)
        self.stick = Control("", (left_mid, low), pad_r)
        gap = round(btn_r * 2.3)
        self.controls = [
            Control("a", (right_mid + gap, low), btn_r, "A"),
            Control("b", (right_mid, low + gap), btn_r, "B"),
            Control("x", (right_mid, low - gap), btn_r, "X"),
            Control("y", (right_mid - gap, low), btn_r, "Y"),
            Control("l", (left_mid, round(height * 0.2)), small_r, "L"),
            Control("r", (right_mid, round(height * 0.2)), small_r, "R"),
            Control("select", (left_mid, round(height * 0.36)), small_r, "SEL"),
            Control("start", (right_mid, round(height * 0.36)), small_r, "ST"),
        ]

    def _below(self, picture: pygame.Rect, width: int, height: int) -> None:
        """Portrait: everything in the space under the picture."""
        top = picture.bottom
        band = height - top
        unit = min(band, width)
        pad_r = max(MIN_RADIUS * 2, round(unit * PAD_SIZE / 3))
        btn_r = max(MIN_RADIUS, round(unit * BUTTON_SIZE / 2.4))
        small_r = max(MIN_RADIUS, round(unit * SMALL_SIZE / 2.4))

        def down(share: float) -> int:
            """A height inside the band, as a share of it."""
            return top + round(band * share)

        # thumbs rest low; the bottom tenth is left clear of the home gesture
        thumbs = down(0.62)
        self.stick = Control("", (round(width * 0.24), thumbs), pad_r)
        right = round(width * 0.72)
        gap = round(btn_r * 2.3)
        self.controls = [
            Control("a", (right + gap, thumbs), btn_r, "A"),
            Control("b", (right, thumbs + gap), btn_r, "B"),
            Control("x", (right, thumbs - gap), btn_r, "X"),
            Control("y", (right - gap, thumbs), btn_r, "Y"),
            Control("l", (round(width * 0.18), down(0.12)), small_r, "L"),
            Control("r", (round(width * 0.82), down(0.12)), small_r, "R"),
            Control("select", (round(width * 0.42), down(0.12)), small_r, "SEL"),
            Control("start", (round(width * 0.58), down(0.12)), small_r, "ST"),
        ]

    def _over(self, width: int, height: int) -> None:
        """No spare room: sit the controls on the picture, see-through."""
        unit = min(height, width // 3)
        pad_r = max(MIN_RADIUS * 2, round(unit * PAD_SIZE / 2))
        btn_r = max(MIN_RADIUS, round(unit * BUTTON_SIZE / 2))
        small_r = max(MIN_RADIUS, round(unit * SMALL_SIZE / 2))
        low = round(height * 0.72)
        left_mid = round(width * 0.14)
        right_mid = round(width * 0.86)
        gap = round(btn_r * 2.3)
        self.stick = Control("", (left_mid, low), pad_r)
        self.controls = [
            Control("a", (right_mid + gap, low), btn_r, "A"),
            Control("b", (right_mid, low + gap), btn_r, "B"),
            Control("x", (right_mid, low - gap), btn_r, "X"),
            Control("y", (right_mid - gap, low), btn_r, "Y"),
            Control("l", (left_mid, round(height * 0.3)), small_r, "L"),
            Control("r", (right_mid, round(height * 0.3)), small_r, "R"),
            Control("select", (round(width * 0.44), round(height * 0.06)), small_r, "SEL"),
            Control("start", (round(width * 0.56), round(height * 0.06)), small_r, "ST"),
        ]

    # ----- fingers -------------------------------------------------------
    def handle(self, event: pygame.event.Event, inp: Input,
               window: tuple[int, int]) -> bool:
        """Feed one event. True if the controls took it."""
        kind = event.type
        if kind in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            point = (round(event.x * window[0]), round(event.y * window[1]))
            finger = int(getattr(event, "finger_id", 0))
        elif kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            if kind == pygame.MOUSEMOTION and not event.buttons[0]:
                return False
            point = event.pos
            finger = -1
        else:
            return False
        if kind in (pygame.FINGERUP, pygame.MOUSEBUTTONUP):
            self._lift(finger)
            self._apply(inp)
            return True
        self._press(finger, point)
        self._apply(inp)
        return bool(self.fingers)

    def _press(self, finger: int, point: tuple[int, int]) -> None:
        """A finger went down, or moved, at a point."""
        if self.stick is not None and self._inside(self.stick, point, slack=1.25):
            self.fingers[finger] = ""
            self._stick_from(point)
            return
        for control in self.controls:
            if self._inside(control, point, slack=1.2):
                self.fingers[finger] = control.action
                return
        self._lift(finger)

    def _lift(self, finger: int) -> None:
        """A finger came up."""
        self.fingers.pop(finger, None)
        if "" not in self.fingers.values():
            self.stick_dirs.clear()

    def _stick_from(self, point: tuple[int, int]) -> None:
        """Turn a point on the pad into up to two directions."""
        assert self.stick is not None
        dx = (point[0] - self.stick.centre[0]) / max(1, self.stick.radius)
        dy = (point[1] - self.stick.centre[1]) / max(1, self.stick.radius)
        self.stick_dirs.clear()
        if dx < -DEAD_ZONE:
            self.stick_dirs.add("left")
        elif dx > DEAD_ZONE:
            self.stick_dirs.add("right")
        if dy < -DEAD_ZONE:
            self.stick_dirs.add("up")
        elif dy > DEAD_ZONE:
            self.stick_dirs.add("down")

    @staticmethod
    def _inside(control: Control, point: tuple[int, int], slack: float = 1.0) -> bool:
        """Is a point on this control? Touch targets are a little generous."""
        reach = control.radius * slack
        dx = point[0] - control.centre[0]
        dy = point[1] - control.centre[1]
        return dx * dx + dy * dy <= reach * reach

    def _apply(self, inp: Input) -> None:
        """Push the current state into the input layer."""
        wanted = set(self.stick_dirs)
        wanted.update(a for a in self.fingers.values() if a)
        for action in self.held - wanted:
            inp.touch(action, False)
        for action in wanted - self.held:
            inp.touch(action, True)
        self.held = wanted

    def release_all(self, inp: Input) -> None:
        """Let go of everything (the window lost focus, or the layout moved)."""
        self.fingers.clear()
        self.stick_dirs.clear()
        self._apply(inp)

    # ----- drawing -------------------------------------------------------
    def draw(self, window: pygame.Surface) -> None:
        """Paint the pad and the buttons over whatever is there.

        The controls only change when a finger moves, so the drawn layer is
        kept and re-blitted. Building it is a full-screen surface with an
        alpha channel, which is far too much work to do sixty times a second
        for a picture that is usually identical to the last one.
        """
        if not self.visible or self.stick is None:
            return
        size = window.get_size()
        key = (size, frozenset(self.held))
        if self._layer is None or self._layer_key != key:
            self._layer = self._render(size)
            self._layer_key = key
        window.blit(self._layer, (0, 0))

    def _render(self, size: tuple[int, int]) -> pygame.Surface:
        """Draw the controls in their current state onto a fresh layer."""
        layer = pygame.Surface(size, pygame.SRCALPHA)
        pad = self.stick
        assert pad is not None
        self._ring(layer, pad.centre, pad.radius, bool(self.stick_dirs))
        pygame.draw.circle(layer, (230, 226, 240, HELD_ALPHA), self._knob(pad),
                           max(4, pad.radius // 3))
        for control in self.controls:
            self._ring(layer, control.centre, control.radius, control.action in self.held)
            if control.label:
                self._label(layer, control)
        return layer

    def _knob(self, pad: Control) -> tuple[int, int]:
        """Where to draw the thumb mark on the pad."""
        dx = (("right" in self.stick_dirs) - ("left" in self.stick_dirs))
        dy = (("down" in self.stick_dirs) - ("up" in self.stick_dirs))
        reach = pad.radius * 0.5
        return (round(pad.centre[0] + dx * reach), round(pad.centre[1] + dy * reach))

    @staticmethod
    def _ring(layer: pygame.Surface, centre: tuple[int, int], radius: int,
              held: bool) -> None:
        alpha = HELD_ALPHA if held else IDLE_ALPHA
        pygame.draw.circle(layer, (16, 14, 26, alpha), centre, radius)
        pygame.draw.circle(layer, (230, 226, 240, alpha + 40), centre, radius,
                           max(2, radius // 12))

    def _label(self, layer: pygame.Surface, control: Control) -> None:
        """The button's letter, in the game's own font, scaled to the button."""
        font = self.font
        if font is None:
            return
        width = max(1, font.measure(control.label))
        glyphs = pygame.Surface((width, 8), pygame.SRCALPHA)
        font.draw(glyphs, control.label, 0, 0, (230, 226, 240))
        # fit the letters inside the ring, however many of them there are
        scale = max(1, min(round(control.radius / 9), int(control.radius * 1.4 / width)))
        shown = pygame.transform.scale(glyphs, (width * scale, 8 * scale))
        shown.set_alpha(220)
        layer.blit(shown, (control.centre[0] - shown.get_width() // 2,
                           control.centre[1] - shown.get_height() // 2))
