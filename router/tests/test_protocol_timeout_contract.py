"""Virtual transport deadline must match actual application socket configuration."""
import importlib.util,sys,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'router/files/usr/lib/homensai-vpn'))
import agent
spec=importlib.util.spec_from_file_location('protocol_lab_timeout',ROOT/'lab/protocol_namespace_lab.py');lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)
class TimeoutContractTests(unittest.TestCase):
 def test_actual_application_socket_uses_lab_deadline(self):
  socket=MagicMock()
  with patch.object(agent.socket,'socket',return_value=socket):agent.bound_socket('wg0',101)
  socket.settimeout.assert_called_once_with(lab.NETWORK_TIMEOUT)
if __name__=='__main__':unittest.main()
