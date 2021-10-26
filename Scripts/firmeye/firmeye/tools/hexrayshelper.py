# -*- coding: utf-8 -*-
# https://github.com/patois/HRDevHelper

import re
import os

import idaapi
import ida_pro
import ida_hexrays
import ida_kernwin
import ida_lines
import ida_graph
import ida_moves
import ida_lines

"""
from firmeye.config import THEME
if THEME == "default":
    from firmeye.view.colors import graph_default as graph_color
elif THEME == "dark":
    from firmeye.view.colors import graph_dark as graph_color
"""
PLUGIN_NAME = "HexraysHelper"

CONFIG = {
    'options':
        {
            'center': True,     # 当前 node 居中
            'zoom': 1.0,        # 1.0 = 100%
            'dockpos': ida_kernwin.DP_RIGHT
        },
    'frame':
        {
            'default': 0x000000,
            'focus': 0xe1ad32,
            'highlight': 0x1baeff
        },
    'node':
        {
            'loop': 0x333366,
            'call': 0x502020,
            'cit': 0x000000,
            'cot': 0x222222
        },
    'text':
        {
            'default': ida_lines.SCOLOR_DEFAULT,
            'highlight': ida_lines.SCOLOR_EXTRA
        }
}

def get_obj_ids(vdui, lnnum):
    obj_ids = []
    pc = vdui.cfunc.get_pseudocode()
    if lnnum >= len(pc):
        return obj_ids
    line = pc[lnnum].line
    tag = ida_lines.COLOR_ON + chr(ida_lines.COLOR_ADDR)
    pos = line.find(tag)
    while pos != -1 and len(line[pos+len(tag):]) >= ida_lines.COLOR_ADDR_SIZE:
        addr = line[pos+len(tag):pos+len(tag)+ida_lines.COLOR_ADDR_SIZE]
        idx = int(addr, 16)
        a = ida_hexrays.ctree_anchor_t()
        a.value = idx
        if a.is_valid_anchor() and a.is_citem_anchor():
            item = vdui.cfunc.treeitems.at(a.get_index())
            if item:
                obj_ids.append(item.obj_id)
        pos = line.find(tag, pos+len(tag)+ida_lines.COLOR_ADDR_SIZE)
    return obj_ids

def get_selected_lines(vdui):
    vdui.get_current_item(ida_hexrays.USE_KEYBOARD)
    line_numbers = []
    w = vdui.ct
    p0 = ida_kernwin.twinpos_t()
    p1 = ida_kernwin.twinpos_t()
    if ida_kernwin.read_selection(w, p0, p1):
        place0 = p0.place(w)
        place1 = p1.place(w)
        a = place0.as_simpleline_place_t(place0).n
        b = place1.as_simpleline_place_t(place1).n
        line_numbers = [i for i in range(a, b+1)]
    else:
        line_numbers = [vdui.cpos.lnnum]
    return line_numbers


class vd_hooks_t(ida_hexrays.Hexrays_Hooks):
    def __init__(self, cg):
        ida_hexrays.Hexrays_Hooks.__init__(self)
        self.cg = cg

    def create_hint(self, vd):
        if vd.get_current_item(ida_hexrays.USE_MOUSE):
            lnnum = vd.cpos.lnnum
            if lnnum < vd.cfunc.hdrlines:
                return 0

            lines = []
            title = "%s:" % PLUGIN_NAME
            sep = 30*"-"
            indent = 2*" "
            
            item = vd.item.it
            op = item.op
            is_expr = item.is_expr()
            item_type = ida_hexrays.get_ctype_name(op)
            item_ea = item.ea
            lines.append("%s" % title)
            lines.append("%s" % (len(title)*"="))
            if is_expr:
                name = item.cexpr.print1(None)
                #name = ida_lines.tag_remove(name)
                #name = ida_pro.str2user(name)
                lines.append("%sitem:\t%s" % (indent, name))
            lines.append("%stype:\tc%ct_%s" % (
                indent,
                "o" if is_expr else "i",
                item_type))
            lines.append("%sea:\t%x" % (indent, item_ea))
            lines.append("%s" % sep)
            lines.append("")
            
            custom_hints = "\n".join(lines)
            return (2, custom_hints, len(lines))
        return 0

    def refresh_pseudocode(self, vu):
        """
        刷新伪代码
        """
        self.cg.update(cfunc=vu.cfunc, focus=None)
        return 0

    def curpos(self, vu):
        # 游标改变时，修改高亮块
        if self.cg:
            objs = []
            line_numbers = get_selected_lines(vu)
            for n in line_numbers:
                objs += get_obj_ids(vu, n)
            focusitem = vu.item.e if vu.item.is_citem() else None
            self.cg.update(cfunc=None, objs=objs, focus=focusitem.obj_id if focusitem else None)
        return 0


class cfunc_graph_t(ida_graph.GraphViewer):
    def __init__(self, focus, config, close_open=False):
        self.title = PLUGIN_NAME
        ida_graph.GraphViewer.__init__(self, self.title, close_open)

        self.center_node = config["options"]["center"]

        self.COLOR_FRAME_DEFAULT = config["frame"]["default"]
        self.COLOR_FRAME_HIGHLIGHT = config["frame"]["highlight"]
        self.COLOR_FRAME_FOCUS = config["frame"]["focus"]

        self.COLOR_NODE_CIT_LOOP = config["node"]["loop"]
        self.COLOR_NODE_COT_CALL = config["node"]["call"]
        self.COLOR_NODE_CIT = config["node"]["cit"]
        self.COLOR_NODE_COT = config["node"]["cot"]

        self.COLOR_TEXT_DEFAULT = config["text"]["default"]
        self.COLOR_TEXT_HIGHLIGHT = config["text"]["highlight"]

        self.items = [] # list of citem_t
        self._set_focus(focus)

        self.objs = []
        self.succs = [] # list of lists of next nodes
        self.preds = [] # list of lists of previous nodes

        self.vd_hooks = vd_hooks_t(self)
        self.vd_hooks.hook()

    def reinit(self):
        self.items = []
        self.succs = []
        self.preds = []
        self.Clear()

    def add_node(self):
        n = self._size()

        def resize(array, new_size):
            if new_size > len(array):
                while len(array) < new_size:
                    array.append([])
            else:
                array = array[:new_size]
            return array

        self.preds = resize(self.preds, n+1)
        self.succs = resize(self.succs, n+1)
        return n

    def add_edge(self, x, y):
        self.preds[y].append(x)
        self.succs[x].append(y)

    def zoom_and_dock(self, vu_title, zoom, dock_position=None):
        widget = ida_kernwin.find_widget(self.title)
        if widget and dock_position:
            gli = ida_moves.graph_location_info_t()
            if ida_graph.viewer_get_gli(gli, widget):
                gli.zoom = zoom
                ida_graph.viewer_set_gli(widget, gli)
            ida_kernwin.set_dock_pos(self.title, vu_title, dock_position)
            self.Refresh()

    def update(self, cfunc=None, objs=None, focus=None):
        if cfunc:
            gb = graph_builder_t(self)
            gb.apply_to(cfunc.body, None)
        self._set_focus(focus)
        self._set_objs(objs)
        self.Refresh()
        return

    def _set_focus(self, focus):
        self.focus = focus

    def _set_objs(self, objs):
        self.objs = objs

    def _nsucc(self, n):
        return len(self.succs[n]) if self._size() else 0

    def _npred(self, n):
        return len(self.preds[n]) if self._size() else 0

    def _succ(self, n, i):
        return self.succs[n][i]

    def _pred(self, n, i):
        return self.preds[n][i]

    def _size(self):
        return len(self.preds)

    def _get_expr_name(self, expr):
        name = expr.print1(None)
        name = ida_lines.tag_remove(name)
        name = ida_pro.str2user(name)
        return name

    def _get_node_label(self, n, highlight_node=False):
        item = self.items[n]
        op = item.op
        insn = item.cinsn
        expr = item.cexpr
        type_name = ida_hexrays.get_ctype_name(op)
        parts = []
        if op == ida_hexrays.cot_ptr:
            parts.append("%s.%d" % (type_name, expr.ptrsize))
        elif op == ida_hexrays.cot_memptr:
            parts.append("%s.%d (m=%d)" % (type_name, expr.ptrsize, expr.m))
        elif op == ida_hexrays.cot_memref:
            parts.append("%s (m=%d)" % (type_name, expr.m,))
        elif op in [
                ida_hexrays.cot_obj,
                ida_hexrays.cot_var]:
            name = self._get_expr_name(expr)
            parts.append("%s.%d %s" % (type_name, expr.refwidth, name))
        elif op in [
                ida_hexrays.cot_num,
                ida_hexrays.cot_helper,
                ida_hexrays.cot_str]:
            name = self._get_expr_name(expr)
            parts.append("%s %s" % (type_name, name,))
        elif op == ida_hexrays.cit_goto:
            parts.append("%s LABEL_%d" % (type_name, insn.cgoto.label_num))
        elif op == ida_hexrays.cit_asm:
            parts.append("%s <asm statements; unsupported ATM>" % type_name)
        else:
            parts.append("%s" % type_name)

        parts.append("ea: %08x" % item.ea)
        if item.is_expr() and not expr.type.empty():
            tstr = expr.type._print()
            parts.append(tstr if tstr else "?")
        scolor = self.COLOR_TEXT_HIGHLIGHT if highlight_node else self.COLOR_TEXT_DEFAULT
        parts = [ida_lines.COLSTR("%s" % part, scolor) for part in parts]
        return "\n".join(parts)

    def _get_node_info(self, n):
        item = self.items[n]
        color = 0
        focus_node = False
        highlight_node = False

        # 判断该 node 是否属于当前伪代码行
        if self.objs is not None and item.obj_id in self.objs:
            highlight_node = True

        if self.focus is not None and item.obj_id == self.focus:
            focus_node = True

        # 处理 COT_
        if item.is_expr():
            # 处理 call 调用
            if item.op == ida_hexrays.cot_call:
                color = self.COLOR_NODE_COT_CALL
            else:
                color = self.COLOR_NODE_COT
        # 处理 CIT_
        elif ida_hexrays.is_loop(item.op):
            color = self.COLOR_NODE_CIT_LOOP
        else:
            color = self.COLOR_NODE_CIT

        return (focus_node, highlight_node, color)

    def OnViewKeydown(self, key, state):
        c = chr(key & 0xFF)

        if c == 'C':
            self.center_node = not self.center_node
            ida_kernwin.msg("%s: centering graph %sabled\n" % (PLUGIN_NAME, "en" if self.center_node else "dis"))
        return True

    def OnClose(self):
        if self.vd_hooks:
            self.vd_hooks.unhook()

    def OnRefresh(self):
        """
        @return: 返回 True 告诉 graph viewer 使用新的 items
        """

        self.nodes = {}
        self.Clear()

        # nodes
        for n in range(len(self.items)):
            item = self.items[n]
            focus_node, highlight_node, color = self._get_node_info(n)
            node_label = self._get_node_label(n, highlight_node=highlight_node)
            nid = self.AddNode((node_label, color))

            framecol = self.COLOR_FRAME_DEFAULT
            if highlight_node:
                framecol = self.COLOR_FRAME_HIGHLIGHT
            if focus_node:
                framecol = self.COLOR_FRAME_FOCUS

            p = idaapi.node_info_t()            
            p.frame_color = framecol
            self.SetNodeInfo(nid, p, idaapi.NIF_FRAME_COLOR)
            self.nodes[item.obj_id] = nid

            if self.center_node and focus_node:
                widget = ida_kernwin.find_widget(self._title)
                ida_graph.viewer_center_on(widget, nid)

        # edges
        for n in range(len(self.items)):
            item = self.items[n]

            for i in range(self._nsucc(n)):
                t = self._succ(n, i)
                self.AddEdge(self.nodes[item.obj_id], self.nodes[self.items[t].obj_id])

        return True

    def OnGetText(self, node_id):
        return self[node_id]
    
    def OnDblClick(self, node_id):
        ida_kernwin.jumpto(self.items[node_id].ea)
        return True

    def OnHint(self, node_id):
        return self._get_node_label(node_id)


class graph_builder_t(ida_hexrays.ctree_parentee_t):

    def __init__(self, cg):
        ida_hexrays.ctree_parentee_t.__init__(self)
        self.init(cg)

    def init(self, cg):
        self.cg = cg
        self.cg.reinit()
        self.reverse = {} # citem_t -> node#

    def _add_node(self, i):
        for k_obj_id in self.reverse.keys():
            if i.obj_id == k_obj_id:
                ida_kernwin.warning("bad ctree - duplicate nodes! (i.ea=%x)" % i.ea)
                return -1

        n = self.cg.add_node()
        if n <= len(self.cg.items):
            self.cg.items.append(i)
        self.cg.items[n] = i
        self.reverse[i.obj_id] = n
        return n

    def _process(self, i):
        n = self._add_node(i)
        if n < 0:
            return n
        if len(self.parents) > 1:
            lp = self.parents.back().obj_id
            for k_obj_id, v in self.reverse.items():
                if k_obj_id == lp:
                    p = v
                    break
            self.cg.add_edge(p, n)
        return 0

    def visit_insn(self, i):
        return self._process(i)

    def visit_expr(self, e):
        return self._process(e)

def get_ctree_graph(ea):
    """
    在当前反编译窗口中创建当前函数的 ctree 图
    """

    vu = ida_hexrays.open_pseudocode(ea, 0)
    w = ida_kernwin.get_current_widget()
    vu_title = ida_kernwin.get_widget_title(w)

    vu.get_current_item(ida_hexrays.USE_KEYBOARD)
    focusitem = vu.item.e if vu.item.is_citem() else None

    # 创建 graphviewer
    cg = cfunc_graph_t(focusitem, CONFIG, close_open=True)
    # 为当前函数创建图像
    gb = graph_builder_t(cg)
    gb.apply_to(vu.cfunc.body, None)
    # 显示图像
    cg.Show()
    # 设置窗口位置
    cg.zoom_and_dock(vu_title, CONFIG["options"]["zoom"], CONFIG["options"]["dockpos"])
