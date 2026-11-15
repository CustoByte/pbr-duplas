"""Replay the real RPBE01 continuation handler; only button input is a fixture."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc


def verify(metrics):
    h = metrics.h
    manager, state, text = 0x81AE0000, 0x81AE1000, 0x81AE2000
    inputs = []
    def button(u, address, size, user):
        inputs.append(u.reg_read(ppc.UC_PPC_REG_3))
        u.reg_write(ppc.UC_PPC_REG_3, 1)  # User presses the advance button.
        u.reg_write(ppc.UC_PPC_REG_PC, u.reg_read(ppc.UC_PPC_REG_LR))
    hook = h.uc.hook_add(UC_HOOK_CODE, button, begin=0x8005B5EC, end=0x8005B5EC)
    cases = []
    try:
        for pages in (1, 2, 3, 5, 8, 16):
            offsets = []
            for index in range(pages):
                h.uc.mem_write(manager, bytes(0x200))
                h.uc.mem_write(state, bytes(0xA0))
                end = index == pages - 1
                payload = b'\xff\xff\xff\xff' if end else b'\xff\xff\xff\xfe\x00P\x00T\xff\xff\xff\xff'
                h.uc.mem_write(text, payload)
                h.uc.mem_write(state + 0x5A, b'\x01')  # Native drawing/advance mode.
                h.put(state + 0x8C, text)
                h.put(state + 0x34, 7); h.put(state + 0x38, 11)
                result = h.call(0x80160A18, (manager, state, 0), limit=3000000)
                h.abi()
                assert result == int(end), (pages, index, result)
                if not end:
                    assert h.get(state) == text + 4, 'Native handler did not skip the page-leading newline'
                    assert h.get(state + 0x48) == 7 and h.get(state + 0x4C) == 11
                    assert struct.unpack('>H', h.uc.mem_read(state + 0x1C, 2))[0] == 1
                offsets.append(dict(boundary=index, reached_end=end, native_result=result))
            cases.append(dict(pages=pages, boundaries=offsets))
    finally:
        h.uc.hook_del(hook)
    return dict(passed=True, native_handler='0x80160a18', native_dispatch='0x8015f0d0',
                button_input_fixture='0x8005b5ec', button_calls=len(inputs), cases=cases,
                no_page_handler_or_text_reset_stubbed=True, gpu_or_actual_menu_tested=False,
                limits=['Validates continuation mechanics; caller-specific UI limits still require conservative gates and Dolphin.'])
