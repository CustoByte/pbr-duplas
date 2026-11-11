"""Assemble a small, version-gated four-Pokemon restoration routine.

The space replaces the obsolete pair-rotation dispatcher in the doubles series
handler. It is not a general code cave. Only the original dispatcher has an
external direct branch into this range; no data pointers were found into it.
"""
import struct

START, END, RESTORE = 0x80076F08, 0x8007707C, 0x80076F20
NOP = 0x60000000


def d(opcode, target, base, immediate):
    return opcode << 26 | target << 21 | base << 16 | (immediate & 0xFFFF)


def mr(target, source):
    return 31 << 26 | source << 21 | target << 16 | source << 11 | 444 << 1


def add(target, first, second):
    return 31 << 26 | target << 21 | first << 16 | second << 11 | 266 << 1


def branch(address, target, link=False):
    displacement = target - address
    if displacement % 4 or not -(1 << 25) <= displacement < (1 << 25):
        raise ValueError('Branch outside signed PowerPC range')
    return 0x48000000 | (displacement & 0x03FFFFFC) | int(link)


def assemble():
    words = {a: NOP for a in range(START, END, 4)}
    words[START] = branch(START, RESTORE, True)
    words[START + 4] = branch(START + 4, END)
    at = RESTORE
    def emit(value):
        nonlocal at
        words[at] = value
        at += 4
    def call(target):
        emit(branch(at, target, True))
    emit(d(37, 1, 1, -0x20))       # stwu r1,-0x20(r1)
    emit(0x7C0802A6)               # mflr r0
    emit(d(36, 0, 1, 0x24))
    emit(d(36, 31, 1, 0x1C))
    emit(d(36, 30, 1, 0x18))
    emit(d(36, 29, 1, 0x14))
    emit(mr(31, 3))
    emit(d(14, 29, 0, 0))         # slot = 0
    loop = at
    for pointer_base, destination in [(0x538, 0x648), (0x550, 0x1420)]:
        emit(21 << 26 | 29 << 21 | 2 << 11 | 29 << 1)  # slwi r0,r29,2
        emit(add(4, 31, 0))
        emit(d(32, 4, 4, pointer_base))
        emit(d(32, 3, 31, 0x30))
        emit(d(7, 30, 29, 0x8C))
        emit(add(3, 3, 30))
        emit(d(14, 3, 3, destination))
        emit(d(14, 5, 0, 0x88))
        call(0x80004000)          # native memcpy, preserving original payload size
        # Restore presence from the original selected Pokemon, preserving the
        # other per-slot bits (including a session resumed after old pair cleanup).
        emit(21 << 26 | 29 << 21 | 2 << 11 | 29 << 1)
        emit(add(4, 31, 0))
        emit(d(32, 4, 4, pointer_base))
        emit(d(34, 4, 4, 0x8A))
        emit(d(32, 3, 31, 0x30))
        emit(add(3, 3, 30))
        emit(d(34, 0, 3, destination + 0x8A))
        emit(20 << 26 | 4 << 21 | 24 << 6 | 24 << 1)  # rlwimi r0,r4,0,24,24
        emit(d(38, 0, 3, destination + 0x8A))
    emit(d(14, 29, 29, 1))
    emit(d(11, 0, 29, 4))         # cmpwi r29,4
    emit(0x41800000 | ((loop - at) & 0xFFFC))  # blt loop
    emit(mr(3, 31))
    emit(d(32, 29, 1, 0x14))
    emit(d(32, 30, 1, 0x18))
    emit(d(32, 31, 1, 0x1C))
    emit(d(32, 0, 1, 0x24))
    emit(0x7C0803A6)               # mtlr r0
    emit(d(14, 1, 1, 0x20))
    emit(0x4E800020)
    if at > END:
        raise ValueError('Restoration routine exceeds replaced dispatcher')
    # Terminal path retains its original callback, reset and manager-state steps.
    words[0x80076E24] = d(32, 3, 13, -0x7E08)
    words[0x80076E28] = branch(0x80076E28, RESTORE, True)
    words[0x80076E2C] = branch(0x80076E2C, 0x80076ED8)
    words[0x800770A0] = d(14, 0, 0, 4)   # session scanning count
    words[0x800770A4] = d(14, 29, 0, 4)  # clear only unused slots 4 and 5
    return words


def bytes_for_range(words, start, end):
    return b''.join(struct.pack('>I', words[a]) for a in range(start, end, 4))
