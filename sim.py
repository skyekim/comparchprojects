#!/usr/bin/python3

"""
Code for simulator that takes machine code as the input and outputs assembly code
"""

from collections import namedtuple
import re
import argparse

# Some helpful constant values that we'll be using.
Constants = namedtuple("Constants",["NUM_REGS", "MEM_SIZE", "REG_SIZE"])
constants = Constants(NUM_REGS = 8, 
                      MEM_SIZE = 2**13,
                      REG_SIZE = 2**16)

def load_machine_code(machine_code, mem):
    """
    Loads an E20 machine code file into the list
    provided by mem. We assume that mem is
    large enough to hold the values in the machine
    code file.
    sig: list(str) -> list(int) -> NoneType
    """
    machine_code_re = re.compile("^ram\[(\d+)\] = 16'b(\d+);.*$")
    expectedaddr = 0
    for line in machine_code:
        match = machine_code_re.match(line)
        if not match:
            raise ValueError("Can't parse line: %s" % line)
        addr, instr = match.groups()
        addr = int(addr,10)
        instr = int(instr,2)
        if addr != expectedaddr:
            raise ValueError("Memory addresses encountered out of sequence: %s" % addr)
        if addr >= len(mem):
            raise ValueError("Program too big for memory")
        expectedaddr += 1
        mem[addr] = instr

def print_state(pc, regs, memory, memquantity):
    """
    Prints the current state of the simulator, including
    the current program counter, the current register values,
    and the first memquantity elements of memory.
    sig: int -> list(int) -> list(int) - int -> NoneType
    """
    print("Final state:")
    print("\tpc="+format(pc,"5d"))
    for reg, regval in enumerate(regs):
        print(("\t$%s=" % reg)+format(regval,"5d"))
    line = ""
    for count in range(memquantity):
        line += format(memory[count], "04x")+ " "
        if count % 8 == 7:
            print(line)
            line = ""
    if line != "":
        print(line)

def main():
    parser = argparse.ArgumentParser(description='Simulate E20 machine')
    parser.add_argument('filename', help='The file containing machine code, typically with .bin suffix')
    cmdline = parser.parse_args()

    # load file and parse using load_machine_code
    mem = [0] * 8192
    with open(cmdline.filename) as file:
        load_machine_code(file, mem)
    file.close()

    # pc, registers
    pc = 0
    condition = True
    registers = [0, 0, 0, 0, 0, 0, 0, 0]

    while condition:
        # the pc is only the 13 least significant bits
        if pc > 8191:
            pc = pc & 8191
        instruction = mem[pc]
        opcode = (instruction & 57344) >> 13
        if opcode == 0:
            # all values need to be unsigned
            srcA = registers[(instruction & 7168) >> 10]
            srcB = registers[(instruction & 896) >> 7]
            dst = (instruction & 112) >> 4
            fourbit = instruction & 15
            # jr
            if fourbit == 8:
                pc = srcA
            else:
                if dst == 0:
                    pc += 1
                else:
                    # add
                    if fourbit == 0:
                        result = srcA + srcB
                        if result < 0:
                            result = result + 65536
                        elif result > 65535:
                            result = result & 65535
                        registers[dst] = result
                    # sub
                    elif fourbit == 1:
                        result = srcA - srcB
                        if result < 0:
                            result = result + 65536
                        registers[dst] = result
                    # or
                    elif fourbit == 2:
                        registers[dst] = srcA | srcB
                    # and
                    elif fourbit == 3:
                        registers[dst] = srcA & srcB
                    # slt
                    elif fourbit == 4:
                        if srcA < srcB:
                            registers[dst] = 1
                        else:
                            registers[dst] = 0
                    pc += 1
        # addi/movi
        elif opcode == 1:
            src = (instruction & 7168) >> 10
            dst = (instruction & 896) >> 7
            imm = (instruction & 127)
            if dst == 0:
                pc += 1
            else: 
                # # imm is signed
                if imm > 63:
                    imm = -128 + imm
                result = registers[src] + imm
                # accounts for overflow
                if result > 65535:
                    result = result & 65535
                # # accounts for negative result
                elif result < 0:
                    result = result + 65536
                registers[dst] = result
                pc += 1
        # j
        elif opcode == 2:
            imm = (instruction & 8191)
            if imm == pc:
                condition = False
                break
            else:
                pc = imm
        # jal
        elif opcode == 3:
            imm = (instruction & 8191)
            registers[7] = (pc + 1) & 8191
            pc = imm
        # lw
        elif opcode == 4:
            addr = (instruction & 7168) >> 10
            dst = (instruction & 896) >> 7
            imm = (instruction & 127)
            if dst == 0:
                pc += 1
            else:
                # imm is signed
                if imm > 63:
                    imm = -128 + imm
                result = imm + registers[addr]
                # accounts for overflow 
                if result > 8191:
                    result = result & 8191
                elif result < 0:
                    result = (result + 65536) & 8191
                registers[dst] = mem[result]
                pc += 1
        # sw
        elif opcode == 5:
            addr = (instruction & 7168) >> 10
            src = (instruction & 896) >> 7
            imm = (instruction & 127)
            # imm is signed
            if imm > 63:
                imm = -128 + imm
            result = imm + registers[addr]
            # accounts for overflow 
            if result > 8191:
                result = result & 8191
            # accounts for negative result
            elif result < 0:
                result = (result + 65536) & 8191
            mem[result] = registers[src]
            pc += 1
        # jeq
        elif opcode == 6:
            regA = (instruction & 7168) >> 10
            regB = (instruction & 896) >> 7
            rel_imm = (instruction & 127)
            if rel_imm > 63:
                rel_imm = -128 + rel_imm
            if registers[regA] == registers[regB]:
                pc = (pc + 1 + rel_imm)
            else:
                pc += 1
        # slti
        elif opcode == 7:
            # values are compared as unsigned values
            src = (instruction & 7168) >> 10
            dst = (instruction & 896) >> 7
            imm = (instruction & 127)
            if dst == 0:
                pc += 1
            else:
                if imm > 63:
                    imm = (-128 + imm) + 65536
                src = registers[src]
                if src < 0:
                    src = 65536 + src
                if src < imm:
                    registers[dst] = 1
                else:
                    registers[dst] = 0
                pc += 1
    print_state(pc, registers, mem, 128)

if __name__ == "__main__":
    main()
#ra0Eequ6ucie6Jei0koh6phishohm9
