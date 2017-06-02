"""Module for the Deutsch-Jozsa Algorithm."""

import pyquil.quil as pq
from pyquil.gates import *
import numpy as np


def oracle_function(unitary_funct, qubits, ancilla, scratch_bit):
    """
    Defines an oracle that performs the following unitary transformation:
    |x>|y> -> |x>|f(x) xor y>

    :param unitary_funct: Matrix representation of the function f, i.e. the
                          unitary transformation that must be applied to a
                          state |x> to put f(x) in qubit 0.
    :param qubits: List of qubits that enter as input |x>.
    :param ancilla: Qubit to serve as input |y>.
    :param scratch_bit: Empty qubit to be used as scratch space.
    :return: A program that performs the above unitary transformation.
    :rtype: Program
    """
    bits_for_funct = [scratch_bit] + qubits
    p = pq.Program()

    p.defgate("FUNCT", unitary_funct)
    p.defgate("FUNCT-INV", np.linalg.inv(unitary_funct))
    p.inst(tuple(['FUNCT'] + bits_for_funct))
    p.inst(CNOT(qubits[0], ancilla))
    p.inst(tuple(['FUNCT-INV'] + bits_for_funct))
    return p


def deutsch_jozsa(oracle, qubits, ancilla):
    """
    Implementation of the Deutsch-Jozsa Algorithm.

    Can determine whether a function f mapping {0,1}^n to {0,1} is constant
    or balanced, provided that it is one of them.

    :param oracle: Program representing unitary application of function.
    :param qubits: List of qubits that enter as state |x>.
    :param ancilla: Qubit to serve as input |y>.
    :return: A program corresponding to the desired instance of the
             Deutsch-Jozsa Algorithm.
    :rtype: Program
    """
    p = pq.Program()

    # Put ancilla bit into minus state
    p.inst(X(ancilla), H(ancilla))

    # Apply Hadamard, Unitary function, and Hadamard again
    p.inst(map(H, qubits))
    p += oracle
    p.inst(map(H, qubits))
    return p

def unitary_function(mappings):
    """
    Creates a unitary transformation that maps each state to the values specified
    in mappings.

    Some (but not all) of these transformations involve a scratch qubit, so one is
    always provided. That is, if given the mapping of n qubits, the calculated transformation
    will be on n + 1 qubits, where the 0th is the scratch bit and the return value
    of the function is left in the 1st.

    :param list mappings: List of the mappings of f(x) on all length n bitstrings.
                          For example, the following mapping:
                          00 -> 0
                          01 -> 1
                          10 -> 1
                          11 -> 0
                          Would be represented as [0, 1, 1, 0].
    :return: Matrix representing specified unitary transformation.
    :rtype: numpy array
    """
    n = int(np.log2(len(mappings)))
    SWAP_matrix = np.array([[1, 0, 0, 0], [0, 0, 1, 0],
                            [0, 1, 0, 0], [0, 0, 0, 1]])

    if sum(mappings) == 0: # Only zeros were entered
        return np.kron(SWAP_matrix, np.identity(2 ** (n - 1)))

    elif sum(mappings) == 2 ** (n - 1): # Half of the entries were 0, half 1
        unitary_funct = np.zeros(shape=(2 ** n, 2 ** n))
        index_lists = [range(2 ** (n - 1)), range(2 ** (n - 1), 2 ** n)]
        for j in range(2 ** n):
            i = index_lists[mappings[j]].pop()
            unitary_funct[i, j] = 1
        return np.kron(np.identity(2), unitary_funct)

    elif sum(mappings) == 2 ** n: # Only ones were entered
        X_gate = np.array([[0, 1], [1, 0]])
        return  np.kron(SWAP_matrix, np.identity(2 ** (n - 1))).dot(
            np.kron(X_gate, np.identity(2 ** n)))
    else:
        assert False, "f(x) must be constant or balanced"


def integer_to_bitstring(x, n):
    return ''.join([str((x >> i) & 1) for i in range(0, n)])

if __name__ == "__main__":
    import pyquil.forest as forest

    # Read function mappings from user
    n = int(input("How many bits? "))
    assert n > 0, "The number of bits must be positive."
    print "Enter f(x) for the following n-bit inputs:"
    mappings = []
    for i in range(2 ** n):
        val = int(input(integer_to_bitstring(i, n) + ': '))
        assert val in [0,1], "f(x) must return only 0 and 1"
        mappings.append(val)

    deutsch_program = pq.Program()
    qubits = [deutsch_program.alloc() for _ in range(n)]
    ancilla = deutsch_program.alloc()
    scratch_bit = deutsch_program.alloc()

    unitary_funct = unitary_function(mappings)
    oracle = oracle_function(unitary_funct, qubits, ancilla, scratch_bit)
    deutsch_program += deutsch_jozsa(oracle, qubits, ancilla)

    print deutsch_program
    qvm = forest.Connection()
    results = qvm.run_and_measure(deutsch_program, [q.index() for q in qubits])
    print "Results:", results
    print "f(x) is", "balanced" if 1 in results[0] else "constant"

