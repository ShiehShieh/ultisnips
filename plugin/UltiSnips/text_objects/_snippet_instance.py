#!/usr/bin/env python
# encoding: utf-8

from UltiSnips.geometry import Position
import UltiSnips._vim as _vim

from UltiSnips.text_objects._base import EditableTextObject, NoneditableTextObject
from UltiSnips.text_objects._parser import TOParser

from ..debug import debug, echo_to_hierarchy

class SnippetInstance(EditableTextObject):
    """
    A Snippet instance is an instance of a Snippet Definition. That is,
    when the user expands a snippet, a SnippetInstance is created to
    keep track of the corresponding TextObjects. The Snippet itself is
    also a TextObject because it has a start an end
    """

    def __init__(self, parent, indent, initial_text, start, end, visual_content, last_re, globals):
        if start is None:
            start = Position(0,0)
        if end is None:
            end = Position(0,0)

        self._cts = 0

        self.locals = {"match" : last_re}
        self.globals = globals
        self.visual_content = visual_content

        EditableTextObject.__init__(self, parent, start, end, initial_text)

        TOParser(self, initial_text, indent).parse(True)

        self.update_textobjects()

    def replace_initital_text(self):
        def _place_initial_text(obj):
            obj.overwrite()

            if isinstance(obj, EditableTextObject):
                for c in obj._childs:
                    _place_initial_text(c)

        _place_initial_text(self)

    def replay_user_edits(self, cmds):
        """Replay the edits the user has done to keep endings of our
        Text objects in sync with reality"""
        debug("---- BEFORE")
        echo_to_hierarchy(self)
        for cmd in cmds:
            self._do_edit(cmd)
        echo_to_hierarchy(self)
        debug("---- AFTER")

    def update_textobjects(self):
        """Update the text objects that should change automagically after
        the users edits have been replayed. This might also move the Cursor
        """
        vc = _VimCursor(self)

        done = set()
        not_done = set()
        def _find_recursive(obj):
            if isinstance(obj, EditableTextObject):
                for c in obj._childs:
                    _find_recursive(c)
            not_done.add(obj)
        _find_recursive(self)

        counter = 10
        while (done != not_done) and counter:
            for obj in sorted(not_done - done): # Order matters for python locals!
                if obj._update(done, not_done):
                    done.add(obj)
            counter -= 1
        if counter == 0:
            raise RuntimeError("Cyclic dependency in TextElements!")

        vc.to_vim()
        self._del_child(vc)

    def select_next_tab(self, backwards = False):
        if self._cts is None:
            return

        if backwards:
            cts_bf = self._cts

            res = self._get_prev_tab(self._cts)
            if res is None:
                self._cts = cts_bf
                return self._tabstops[self._cts]
            self._cts, ts = res
            return ts
        else:
            res = self._get_next_tab(self._cts)
            if res is None:
                self._cts = None
                return self._tabstops[0]
            else:
                self._cts, ts = res
                return ts

        return self._tabstops[self._cts]

    def _get_tabstop(self, requester, no):
        # SnippetInstances are completely self contained, therefore, we do not
        # need to ask our parent for Tabstops
        p = self._parent
        self._parent = None
        rv = EditableTextObject._get_tabstop(self, requester, no)
        self._parent = p

        return rv


class _VimCursor(NoneditableTextObject):
    """Helper class to keep track of the Vim Cursor"""

    def __init__(self, parent):
        NoneditableTextObject.__init__(
            self, parent, _vim.buf.cursor, _vim.buf.cursor
        )

    def to_vim(self):
        assert(self._start == self._end)
        _vim.buf.cursor = self._start
