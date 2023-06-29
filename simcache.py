#!/usr/bin/python3

"""
Code for the cache simulator which takes assembly code and a cache and outputs the correct cache configuration
"""

import re
import argparse
    
def print_cache_config(cache_name, size, assoc, blocksize, num_rows):
    """
    Prints out the correctly-formatted configuration of a cache.

    cache_name -- The name of the cache. "L1" or "L2"

    size -- The total size of the cache, measured in memory cells.
        Excludes metadata

    assoc -- The associativity of the cache. One of [1,2,4,8,16]

    blocksize -- The blocksize of the cache. One of [1,2,4,8,16,32,64])

    num_rows -- The number of rows in the given cache.

    sig: str, int, int, int, int -> NoneType
    """

    summary = "Cache %s has size %s, associativity %s, " \
        "blocksize %s, rows %s" % (cache_name,
        size, assoc, blocksize, num_rows)
    print(summary)

def print_log_entry(cache_name, status, pc, addr, row):
    """
    Prints out a correctly-formatted log entry.

    cache_name -- The name of the cache where the event
        occurred. "L1" or "L2"

    status -- The kind of cache event. "SW", "HIT", or
        "MISS"

    pc -- The program counter of the memory
        access instruction

    addr -- The memory address being accessed.

    row -- The cache row or set number where the data
        is stored.

    sig: str, str, int, int, int -> NoneType
    """
    log_entry = "{event:8s} pc:{pc:5d}\taddr:{addr:5d}\t" \
        "row:{row:4d}".format(row=row, pc=pc, addr=addr,
            event = cache_name + " " + status)
    print(log_entry)

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

# change to return result
def readjust(result):
    if result < 0:
        result = result + 65536
    elif result > 65535:
        result = result & 65535
    else:
        result = result

# fuction to calculate tag/row
def calculate(result, blocksize, num_rows):
    block = result // blocksize
    row = block % num_rows
    tag = block // num_rows
    return row, tag

# fuction for eviction
def evict(cache, row, assoc, tag):
    if len(cache[row]) == assoc:
        evict = cache[row][0]
        cache[row].remove(evict)
    cache[row].append(tag)


def main():
    parser = argparse.ArgumentParser(description='Simulate E20 cache')
    parser.add_argument('filename', help=
        'The file containing machine code, typically with .bin suffix')
    parser.add_argument('--cache', help=
        'Cache configuration: size,associativity,blocksize (for one cache) '
        'or size,associativity,blocksize,size,associativity,blocksize (for two caches)')
    cmdline = parser.parse_args()

    # L1 and L2 caches
    L1cache = []
    L2cache = []

    if cmdline.cache is not None:
        parts = cmdline.cache.split(",")
        if len(parts) == 3:
            [L1size, L1assoc, L1blocksize] = [int(x) for x in parts]

            # calculates num_rows 
            num_rows = L1size // (L1blocksize * L1assoc)

            # creates cache table
            for i in range(num_rows):
                L1cache.append([])

            print_cache_config("L1", L1size, L1assoc, L1blocksize, num_rows)

        elif len(parts) == 6:
            [L1size, L1assoc, L1blocksize, L2size, L2assoc, L2blocksize] = \
                [int(x) for x in parts]

            # calculates num_rows
            L1num_rows = L1size // (L1blocksize * L1assoc)
            L2num_rows = L2size // (L2blocksize * L2assoc)

            # creates cache table
            for i in range(L1num_rows):
                L1cache.append([])
            for i in range(L2num_rows):
                L2cache.append([])

            print_cache_config("L1", L1size, L1assoc, L1blocksize, L1num_rows)
            print_cache_config("L2", L2size, L2assoc, L2blocksize, L2num_rows)
        else:
            raise Exception("Invalid cache config")
        
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
            leastsig = pc & 8191
            instruction = mem[leastsig]
        else:
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
                        readjust(result)
                        registers[dst] = result
                    # sub
                    elif fourbit == 1:
                        result = srcA - srcB
                        readjust(result)
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
                readjust(result)
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
                
                if len(parts) == 3:
                    # calculates row/tag
                    row, tag = calculate(result, L1blocksize, num_rows)

                    if tag not in L1cache[row]:
                        evict(L1cache, row, L1assoc, tag)
                        status = "MISS"
                    else:
                        L1cache[row].remove(tag)
                        L1cache[row].append(tag)
                        status = "HIT"

                    print_log_entry("L1", status, pc, result, row)
                
                elif len(parts) == 6:
                    L1row, L1tag = calculate(result, L1blocksize, L1num_rows)
                    L2row, L2tag = calculate(result, L2blocksize, L2num_rows)

                    if L1tag not in L1cache[L1row]:
                        evict(L1cache, L1row, L1assoc, L1tag)
                        L1status = "MISS"
                    else:
                        L1cache[L1row].remove(L1tag)
                        L1cache[L1row].append(L1tag)
                        L1status = "HIT"

                    print_log_entry("L1", L1status, pc, result, L1row)
                    if L1status == "MISS":
                        if L2tag not in L2cache[L2row]:
                            evict(L2cache, L2row, L2assoc, L2tag)
                            L2status = "MISS"
                        else:
                            L2cache[L2row].remove(L2tag)
                            L2cache[L2row].append(L2tag)
                            L2status = "HIT"
                        print_log_entry("L2", L2status, pc, result, L2row)    
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

            if len(parts) == 3:
                row, tag = calculate(result, L1blocksize, num_rows)

                if tag not in L1cache[row]:
                    evict(L1cache, row, L1assoc, tag)
                else:
                    L1cache[row].remove(tag)
                    L1cache[row].append(tag)

                print_log_entry("L1", "SW", pc, result, row)

            elif len(parts) == 6:
                L1row, L1tag = calculate(result, L1blocksize, L1num_rows)
                L2row, L2tag = calculate(result, L2blocksize, L2num_rows)
                
                if L1tag not in L1cache[L1row]:
                    evict(L1cache, L1row, L1assoc, L1tag)
                else:
                    L1cache[L1row].remove(L1tag)
                    L1cache[L1row].append(L1tag)

                print_log_entry("L1", "SW", pc, result, L1row)

                if L2tag not in L2cache[L2row]:
                    evict(L2cache, L2row, L2assoc, L2tag)
                else:
                    L2cache[L2row].remove(L2tag)
                    L2cache[L2row].append(L2tag)
                print_log_entry("L2", "SW", pc, result, L2row)
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

if __name__ == "__main__":
    main()
#ra0Eequ6ucie6Jei0koh6phishohm9
