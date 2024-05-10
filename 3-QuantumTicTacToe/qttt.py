__author__ = 'QRL_team'

import numpy as np
from gym import spaces
from itertools import permutations
from qiskit import (
    QuantumCircuit,
    transpile)
from qiskit.circuit.library import (
    HGate,
    XGate,
    CXGate)
from qiskit_aer import Aer


class QTicTacToeEnv:
    def __init__(self, grid_size):
        """
        Inits a QTTT environmen
        :param grid_size: linear size of the board
        """
        # select simulators
        self.simulator = Aer.get_backend('qasm_simulator')
        self.statevec_sim = Aer.get_backend('statevector_simulator')
        # one qubit for each tile of the board
        self.qnum = grid_size ** 2
        # init board circuit
        self.circuit = QuantumCircuit(self.qnum)
        # init moves dictionary
        self.moves = self._init_moves_dict()
        # init action space as a gym space obj, so that agents can interpret it
        self.action_space = spaces.Discrete(len(self.moves))
        # init dictionary of possible final board configs
        self.endings_lookuptable = self._init_outcomes_dict()
        # not necessary, saves the moves
        self.status_id = ""

    def _init_moves_dict(self):
        """
        Generates a dictionary with all possible moves.
        Possible moves are: place H or X on a chosen qubit; apply a CNOT at chosen quibits pair
        :return: a dict with int keys and tuples of (qubits, qiskit gates) as values
        """
        mvs_dict = {}
        mv_indx = 0
        for q in range(self.qnum):
            mvs_dict[mv_indx] = ([q], HGate())
            mv_indx += 1
            mvs_dict[mv_indx] = ([q], XGate())
            mv_indx += 1
        for (c, t) in permutations(list(range(self.qnum)), 2):
            mvs_dict[mv_indx] = ([c, t], CXGate())
            mv_indx += 1
        return mvs_dict

    def _win_check(self, board):
        """
        Checks for game result
        :param board: string representing the final state of the board
        :return: winning player (1 or 2) or draw flag (0)
        """
        d = int(np.sqrt(self.qnum))
        # transofrm board string to rows, cols and diags
        rows = [board[i*d:(i+1)*d] for i in range(d)]
        cols = ["".join([rows[i][j] for i in range(d)]) for j in range(d)]
        diags = ["".join([rows[i][i] for i in range(d)]), "".join([rows[i][d-i-1] for i in range(d)])]
        winner = 0
        # winning conditions for players 1 and 2
        cond_1 = bin(0)[2:].zfill(d)
        cond_2 = bin(2**d - 1)[2:].zfill(d)
        # check each line and exit if both player win
        for line in [*rows, *cols, *diags]:
            if line == cond_1:
                if winner == 0 or winner == 1:
                    winner = 1
                elif winner == 2:
                    return 0  # because both players won
            elif line == cond_2:
                if winner == 0 or winner == 2:
                    winner = 2
                elif winner == 1:
                    return 0  # because both players won

        return winner

    def _init_outcomes_dict(self):
        """
        Inits a dictionary with all possible endings
        :return: a dict whose keys are the winning player or a draw flag (0) and whose associated values
        are all the final board configs leading to such outcome
        """
        out_dict = {1: [], 2: [], 0: []}
        # init all possible observed board states
        all_states = [bin(x)[2:].zfill(self.qnum) for x in range(2**self.qnum)]
        for state in all_states:
            winner = self._win_check(state)
            out_dict[winner].append(int(state, 2))

        return out_dict

    def move(self, action):
        """
        Take the action by appending the associated gate to the board circ.
        :param action: int, key of the moves dict
        :return:
        """
        self.status_id += "{}-".format(action)
        self.circuit.append(self.moves[action][1], self.moves[action][0])

    def _get_statevec(self):
        """
        Quantumly observe the board, return the "percept" as the statevector of the board circuit
        :return: rounded state vec of the board
        """
        new_circuit = transpile(self.circuit, self.statevec_sim)
        job = self.statevec_sim.run(new_circuit)
        result = job.result()
        output_state = result.get_statevector()
        return np.around(output_state, decimals=2)

    def collapse_board(self):
        """
        Final move, measure the board and observe final state
        :return: final classical state of the board
        """
        self.circuit.measure_all()
        new_circuit = transpile(self.circuit, self.simulator)
        job = self.simulator.run(new_circuit, shots=1)
        res = job.result()
        counts = res.get_counts()
        collapsed_state = int(list(counts.keys())[0][:self.qnum], 2)
        return collapsed_state

    def check_end(self, board_state):
        """
        Check for ending
        :param board_state: classical board state after collapse
        :return: winning player (1 or 2) or draw flag (0)
        """
        if board_state in self.endings_lookuptable[1]:
            print("\nPlayer 1 wins!!!\n")
            return 1
        elif board_state in self.endings_lookuptable[2]:
            print("\nPlayer 2 wins!!!\n")
            return 2
        else:
            print("\nIt's a draw!\n")
            return 0

    def step(self, action):
        """
        Perform the chosen action on the board
        :param action: int representing the chosen action
        :return: new_state of the board, reward (static), done=False
        """
        self.move(action)
        new_state = self._get_statevec()
        reward = -0.1
        return new_state, reward, False

    def reset(self):
        """
        Resets the board
        :return:
        """
        self.circuit = QuantumCircuit(self.qnum, self.qnum)
        self.circuit.h(list(range(self.qnum)))
        self.status_id = ""
        return self._get_statevec()

    def render(self):
        # TODO: devise a render function
        return 0
