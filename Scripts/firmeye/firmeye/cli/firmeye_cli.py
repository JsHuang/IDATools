# -*- coding: utf-8 -*-

import os

import ida_pro

from firmeye.utility import SINK_FUNC, FUNC_TAG, MEMORY
from firmeye.helper import hexstr
from firmeye.analysis.static import FESinkFuncMgr, printf_func_analysis, str_func_analysis, scanf_func_analysis, system_func_analysis, mem_func_analysis

def analysis():
    f = open('analyze_result.txt', 'w+')
    result = []
    mgr_t = FESinkFuncMgr()

    for func_name, xref_list in mgr_t.gen_sink_func_xref():
        tag = SINK_FUNC[func_name]['tag']
        if tag == FUNC_TAG['PRINTF']:
            items = printf_func_analysis(func_name, xref_list)
            result += build_result(items)
        elif tag == FUNC_TAG['STRING']:
            items = str_func_analysis(func_name, xref_list)
            result += build_result(items)
        elif tag == FUNC_TAG['SCANF']:
            items = scanf_func_analysis(func_name, xref_list)
            result += build_result(items)
        elif tag == FUNC_TAG['SYSTEM']:
            items = system_func_analysis(func_name, xref_list)
            result += build_result(items)
        elif tag == FUNC_TAG['MEMORY']:
            items = mem_func_analysis(func_name, xref_list)
            result += build_result(items)
        else:
            continue

    f.writelines(result)
    f.close

def build_result(items):
    lines = []
    for item in items:
        data = [str(item.vuln), item.name, hexstr(item.ea)]
        for x in [item.addr1, item.addr2]:
            if x != None:
                data.append(hexstr(x))
            else:
                continue
        for x in [item.str1, item.str2, item.other1]:
            if x != None:
                data.append(repr(x))
            else:
                continue
        data.append('\n')
        lines.append('\t'.join(data))
    return lines

if __name__ == "__main__":
    analysis()
    if "DO_EXIT" in os.environ:
        ida_pro.qexit(1)
