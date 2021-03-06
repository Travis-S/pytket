# Copyright 2019 Cambridge Quantum Computing
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
from qiskit.converters import dag_to_circuit
from qiskit import IBMQ, QuantumCircuit
from qiskit.compiler import assemble
from qiskit.tools.monitor import job_monitor

from pytket.backends.measurements import bin_str_2_table
from pytket.backends import Backend
from pytket.qiskit import tk_to_dagcircuit
from pytket._routing import route, Architecture
from pytket._transform import Transform
from pytket._circuit import Circuit
import numpy as np

def routed_ibmq_circuit(circuit:Circuit, arc: Architecture) -> QuantumCircuit:
    physical_c = route(circuit, arc)
    physical_c.decompose_SWAP_to_CX()
    physical_c.redirect_CX_gates(arc)
    Transform.OptimisePostRouting().apply(physical_c)

    dag = tk_to_dagcircuit(physical_c)
    qc = dag_to_circuit(dag)

    return qc


class IBMQBackend(Backend) :
    def __init__(self, backend_name:str, monitor:bool=True) :
        """A backend for running circuits on remote IBMQ devices.

        :param backend_name: name of ibmq device. e.g. `ibmqx4`, `ibmq_16_melbourne`.
        :type backend_name: str
        :param monitor: Use IBM job monitor, defaults to True
        :type monitor: bool, optional
        :raises ValueError: If no IBMQ account has been set up.
        """
        if len(IBMQ.stored_accounts()) ==0:
            raise ValueError('No IBMQ credentials found on disk. Store some first.')
        IBMQ.load_accounts()
        self._backend = IBMQ.get_backend(backend_name)
        coupling = self._backend.configuration().coupling_map
        self.architecture = Architecture(coupling)
        self._monitor = monitor
    
    def run(self, circuit:Circuit, shots:int) -> np.ndarray :
        qc = routed_ibmq_circuit(circuit, self.architecture)
        qobj = assemble(qc, shots=shots, memory=True)
        job = self._backend.run(qobj)
        if self._monitor :
            job_monitor(job)
        
        shot_table = bin_str_2_table(job.result().get_memory(qc))
        return shot_table
