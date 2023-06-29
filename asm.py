#!/usr/bin/python3

"""
Code for assembler that takes assembly code as the input and outputs machine code
"""

import argparse

opcodes = {"add" : 0b000, "sub" : 0b000, "or" : 0b000, "and" : 0b000, "stl" : 0b000, 
    "jr" : 0b000, "slti" : 0b111, "lw" : 0b100, "sw" : 0b101, "jeq" : 0b110, "addi" : 0b001,
    "j" : 0b010, "jal" : 0b011, "movi" : 0b001, "nop" : 0b000, ".fill" : 0b000, "halt" : 0b010}


labels = {}

def print_machine_code(address, num):
    """
    print_line(address, num)
    Print a line of machine code in the required format.
    Parameters:
        address: int = RAM address of the instructiontions
        num: int = numeric value of machine instructiontion 

    For example: 
        >>> print_machine_code(3, 42)
        ram[3] = 16'b0000000000101010;    
    """
    instructiontion_in_binary = format(num,'016b')
    print("ram[%s] = 16'b%s;" % (address, instructiontion_in_binary))

# adds label and halt to dictionary with value
def assign_labels(instruction_list):
    address = 0
    for lst in instruction_list:
        opcode = lst[0].strip(":")
        check = opcode in opcodes
        if check == False:
            labels[opcode] = address 
            if len(lst) > 1:
                address += 1
        else:
            address += 1
            
    location = 0
    for lst in instruction_list:
        opcode = lst[0].strip(":")
        if opcode == "halt":
            labels["halt"] = location
            location += 1
        elif (len(lst) > 1 and lst[1] == "halt"):
            labels["halt"] = location
        elif opcode not in labels: 
            location += 1
    return instruction_list

# generates machine code for instructiontions with three register arguments
def three_reg(arg, opcode):
    dst = int(arg[0])
    srcA = int(arg[1])
    srcB = int(arg[2])

    if opcode == "add":
        op = opcodes["add"]
        imm = 0b0000
    elif opcode == "sub":
        op = opcodes["sub"]
        imm = 0b0001
    elif opcode == "or":
        op = opcodes["or"] 
        imm = 0b0010
    elif opcode == "and":
        op = opcodes["and"]
        imm = 0b0011
    elif opcode == "slt":
        op = opcodes["stl"]
        imm = 0b0100

    return (op << 13) | (srcA << 10) | (srcB << 7) | (dst << 4) | imm

# generates machine code for instructiontions with two register arguments
def two_reg(arg, opcode):
    dst = int(arg[0])
    reg = 0b000
    if opcode == "slti":
        op = opcodes["slti"]
        reg = int(arg[1])
        imm = arg[2]
    elif opcode == "lw": # has imm($regAddr) syntax
        op = opcodes["lw"]
        word = arg[1]
        par1 = word.find("(")
        par2 = word.find(")")
        imm = word[0:par1]
        reg = int(word[par1 + 2: par2])
    elif opcode == "sw": # has imm($regAddr) syntax
        op = opcodes["sw"]
        word = arg[1]
        par1 = word.find("(")
        par2 = word.find(")")
        imm = word[0:par1]
        reg = int(word[par1 + 2: par2])
    elif opcode == "addi": # movi is the same 
        op = opcodes["addi"]
        reg = int(arg[1])
        imm = arg[2]
    else:
        op = opcodes["movi"]
        dst = int(arg[0])
        imm = arg[1]

    if imm in labels:
        imm = labels[imm]
    elif int(imm) < 0:
        imm = (int(imm) + 65536) & 127
    else:
        imm = int(imm) & 127
    
    return (op << 13) | (reg << 10) | (dst << 7) | imm

def jump_instructiontion(arg, opcode):
    if opcode == "j":
        op = opcodes["j"]
    elif opcode == "jal":
        op = opcodes["jal"]

    imm = arg[0]
    if imm in labels:
        imm = labels[imm]
    elif int(imm) < 0:
        imm = (int(imm) + 65536) & 127
    else:
        imm = int(imm) & 127

    return (op << 13) | (imm & 8191)


def main():
    parser = argparse.ArgumentParser(description='Assemble E20 files into machine code')
    parser.add_argument('filename', help='The file containing assembly language, typically with .s suffix')
    cmdline = parser.parse_args()

    # our final output is a list of ints values representing
    # machine code instructiontions
    instructiontions=[]

    instruction_list = []

    # iterate through the line in the file, construct a list
    # of numeric values representing machine code
    with open(cmdline.filename) as f:
        for line in f:
            line = line.lower().split("#",1)[0].strip()    # remove comments and leading/trailing whitespace, makes all lowercase
            if len(line) != 0: 
                line = line.split(" ", 1) # splits line between opcode and registers
                instruction_list.append(line)
    f.close()

    # ASSIGNS ADDRESSES TO LABELS
    instruction_list = assign_labels(instruction_list)

    # goes through list of instructiontions
    for instruction in instruction_list:
        # removes single labels from instructiontion list
        if (len(instruction) == 1) and ((instruction[0].strip(":")) in labels) and ((instruction[0].strip(":")) != "halt"):
            instruction_list.remove(instruction)
    pc = 0 # to keep track of program counter
    # goes through instructiontions that has no labels
    for instruction in instruction_list:
        mc = 0 # machine code
        opcode = instruction[0] # opcode
        if len(instruction) > 1:
            arg = instruction[1].split(",") # list of registers/instructiontion without opcode
            # checks if label and instructiontion are on the same line and removes label if necessary 
            if opcode not in opcodes:
                if len(arg) > 1:
                    idx = arg[0].find(" ")
                    opcode = arg[0][:idx]
                    arg[0] = arg[0][idx:]
                else:
                    opcode = arg[0]
                    arg = instruction[1:]
            # removes $ from registers only numbers and labels are left
            for i in range(len(arg)):
                arg[i] = arg[i].strip("$ ")
            # three register instructiontion
            if opcode == "add" or opcode == "sub" or opcode == "or" or opcode == "and" or opcode == "slt":
                mc = three_reg(arg, opcode)
            # two register instructiontion
            elif opcode == "slti" or opcode == "lw" or opcode == "sw" or opcode == "addi" or opcode == "movi":
                mc = two_reg(arg, opcode)
            # jump instructiontions
            elif opcode == "j" or  opcode == "jal":
                mc = jump_instructiontion(arg, opcode)
            elif opcode == "jr":  
                reg = int(arg[0])
                srcA = 0b000
                srcB = 0b000
                imm = 0b1000
                mc = (opcodes["jr"] << 13) | (reg << 10) | (srcA << 7) | (srcB << 4) | imm
            elif opcode == "jeq":
                regA = int(arg[0])
                regB = int(arg[1])
                imm = arg[2]
                if imm in labels:
                    imm = labels[imm]
                elif int(imm) < 0:
                    imm = (int(imm) + 65536) & 127
                else:
                    imm = int(imm) & 127
                rel_imm = imm - pc - 1
                if rel_imm < 0:
                    rel_imm += 128
                mc = (opcodes["jeq"] << 13) | (regA << 10) | (regB << 7) | (rel_imm & 127)

            # pseudo instructiontions
            elif opcode == ".fill":
                mc = int(arg[0]) & 65535

            elif opcode == "nop":
                mc = 0 & 65535
            elif opcode == "halt":
                mc = (0b010 << 13) | (labels["halt"] & 8191)

        else:
            if opcode == "nop":
                mc = 0 & 65535
            elif opcode == "halt":
                mc = (0b010 << 13) | (labels["halt"] & 8191)

        instructiontions.append(mc)
        pc += 1

    # print out each instructiontion in the required format
    for address, instructiontion in enumerate(instructiontions):
        print_machine_code(address, instructiontion) 


if __name__ == "__main__":
    main()

#ra0Eequ6ucie6Jei0koh6phishohm9
